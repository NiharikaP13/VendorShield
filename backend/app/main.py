"""VendorShield FastAPI backend."""
from __future__ import annotations
import csv, os, threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from backend.app import database, model_service, security, workflow
from backend.app.schemas import LoginRequest,LoginResponse,RegisterRequest,ReviewUpdate,NoteCreate,EvidenceUpdate,TransactionBusinessInput
ROOT=Path(__file__).resolve().parents[2]
@asynccontextmanager
async def lifespan(_:FastAPI):
    workflow.migrate()
    # add optional transaction columns without rebuilding historical data
    with database.connect() as c:
        cols={r[1] for r in c.execute('PRAGMA table_info(transactions)')}
        if 'purchase_order_number' not in cols: c.execute("ALTER TABLE transactions ADD COLUMN purchase_order_number TEXT DEFAULT ''")
        if 'source' not in cols: c.execute("ALTER TABLE transactions ADD COLUMN source TEXT DEFAULT 'Historical Portfolio'")
        c.commit()
    threading.Thread(target=model_service.warm_model,daemon=True).start(); threading.Thread(target=database.warm_cache,daemon=True).start(); yield
app=FastAPI(title='VendorShield Auditor API',version='5.0.0',lifespan=lifespan,description=workflow.DISCLAIMER)
_origins=os.environ.get('VENDORSHIELD_CORS_ORIGINS','*')
app.add_middleware(CORSMiddleware,allow_origins=['*'] if _origins=='*' else [x.strip() for x in _origins.split(',')],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
Auth=Annotated[security.AuthContext,Depends(security.require_auth)]
def fail(exc:Exception,code=400): raise HTTPException(code,str(exc)) from exc

def filters(vendor_id,risk_level,category,region,payment_method,review_status,date_from,date_to,min_probability,shell_only,search):
 return {'vendor_id':vendor_id,'risk_level':risk_level,'category':category,'region':region,'payment_method':payment_method,'review_status':review_status,'date_from':date_from,'date_to':date_to,'min_probability':min_probability,'shell_only':shell_only,'search':search}
@app.get('/health')
def health():
 try:return {'status':'ok','model':model_service.model_status(),**database.health()}
 except Exception as e: fail(e,503)
@app.post('/auth/register')
def register(b:RegisterRequest): return security.register(b.name,b.email,b.password,b.department,b.employee_id)
@app.post('/auth/login',response_model=LoginResponse)
def login(b:LoginRequest):
 token,c=security.issue_token(b.username,b.password); return LoginResponse(access_token=token,expires_in_seconds=security.TOKEN_TTL_SECONDS,username=c.username,email=c.email,role=c.role,display_name=c.display_name,auditor_id=c.auditor_id)
@app.post('/auth/logout')
def logout(auth:Auth,authorization:str|None=Header(default=None)):
 if authorization and authorization.lower().startswith('bearer '): security.revoke_token(authorization.split(' ',1)[1].strip())
 return {'message':'Signed out successfully.'}
@app.get('/auth/profile')
def profile(auth:Auth): return workflow.profile(auth.auditor_id)
@app.get('/dashboard/options')
def options(_:Auth): return database.options()
@app.get('/dashboard/summary')
def summary(_:Auth,vendor_id:list[str]|None=Query(None),risk_level:list[str]|None=Query(None),category:list[str]|None=Query(None),region:list[str]|None=Query(None),payment_method:list[str]|None=Query(None),review_status:list[str]|None=Query(None),date_from:str|None=None,date_to:str|None=None,min_probability:float|None=Query(None,ge=0,le=1),shell_only:bool=False,search:str|None=None):
 return database.summary(filters(vendor_id,risk_level,category,region,payment_method,review_status,date_from,date_to,min_probability,shell_only,search))
@app.get('/transactions')
def transactions(_:Auth,page:int=Query(1,ge=1),page_size:int=Query(50,ge=10,le=200),sort_by:str='fraud_probability',sort_order:str='desc',vendor_id:list[str]|None=Query(None),risk_level:list[str]|None=Query(None),category:list[str]|None=Query(None),region:list[str]|None=Query(None),payment_method:list[str]|None=Query(None),review_status:list[str]|None=Query(None),date_from:str|None=None,date_to:str|None=None,min_probability:float|None=Query(None,ge=0,le=1),shell_only:bool=False,search:str|None=None):
 return database.list_transactions(filters(vendor_id,risk_level,category,region,payment_method,review_status,date_from,date_to,min_probability,shell_only,search),page,page_size,sort_by,sort_order)
@app.get('/transactions/{purchase_id}')
def transaction(purchase_id:str,_:Auth):
 r=database.transaction_detail(purchase_id)
 if not r: raise HTTPException(404,'Transaction not found.')
 inp={k:r[k] for k in model_service.FEATURE_COLUMNS}; pred=model_service.score_one(inp); r.pop('fraud_label',None); r.pop('fraud_reason',None); r['top_reasons']=pred.get('top_reasons',[]); r['decision_support_note']=workflow.DISCLAIMER; return r
@app.post('/assessments/derive')
def derive(b:TransactionBusinessInput,_:Auth):
 try:
  m,p=workflow.derive_features(b.model_dump()); pred=model_service.score_one(m); return {'model_inputs':m,'provenance':p,'prediction':pred,'business_inputs':b.model_dump(),'disclaimer':workflow.DISCLAIMER}
 except Exception as e: fail(e,422)
@app.post('/assessments/save')
def save(b:TransactionBusinessInput,auth:Auth):
 try:
  m,p=workflow.derive_features(b.model_dump()); pred=model_service.score_one(m); saved=workflow.save_assessment(auth.auditor_id,b.model_dump(),m,pred); return {**saved,'provenance':p}
 except Exception as e: fail(e,422)
@app.post('/assessments/extract-pdf')
async def extract_pdf(auth:Auth,file:UploadFile=File(...)):
 if file.content_type!='application/pdf' or not file.filename.lower().endswith('.pdf'): raise HTTPException(415,'Only PDF files are supported.')
 data=await file.read()
 if len(data)>10*1024*1024: raise HTTPException(413,'PDF must be 10 MB or smaller.')
 try:return workflow.extract_pdf(data)
 except Exception as e: fail(e,422)
@app.post('/cases/{purchase_id}/open')
def open_case(purchase_id:str,auth:Auth):
 try:return workflow.create_or_open_case(purchase_id,auth.auditor_id)
 except Exception as e: fail(e,404)
@app.get('/cases')
def cases(auth:Auth,status:str|None=None): return {'items':workflow.list_cases(auth.auditor_id,status)}
@app.get('/cases/{case_id}')
def case(case_id:str,auth:Auth):
 try:return workflow.case_bundle(case_id,auth.auditor_id)
 except Exception as e: fail(e,404)
@app.patch('/cases/{case_id}')
def case_update(case_id:str,b:ReviewUpdate,auth:Auth):
 try:return workflow.update_case(case_id,auth.auditor_id,b.model_dump())
 except Exception as e: fail(e,404)
@app.post('/cases/{case_id}/notes')
def note(case_id:str,b:NoteCreate,auth:Auth):
 try:return workflow.add_note(case_id,auth.auditor_id,b.content,b.important,b.note_type)
 except Exception as e: fail(e,404)
@app.patch('/cases/{case_id}/evidence/{item_id}')
def evidence(case_id:str,item_id:int,b:EvidenceUpdate,auth:Auth):
 try:return workflow.update_evidence(case_id,item_id,auth.auditor_id,b.status,b.comment)
 except Exception as e: fail(e,404)
@app.get('/cases/{case_id}/report')
def report(case_id:str,auth:Auth):
 try:return Response(workflow.case_report(case_id,auth.auditor_id),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="{case_id}.pdf"'})
 except Exception as e: fail(e,500)
@app.get('/suppliers/{vendor_id}')
def supplier(vendor_id:str,_:Auth):
 try:return workflow.supplier_profile(vendor_id)
 except Exception as e: fail(e,404)
@app.get('/model/global-importance')
def importance(_:Auth):
 with (ROOT/'backend/model/shap_global_importance.csv').open(encoding='utf-8') as h: rows=list(csv.DictReader(h))
 return {'items':rows}

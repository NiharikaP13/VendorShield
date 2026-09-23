from __future__ import annotations
import uuid, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.app.main import app

def run():
 with TestClient(app) as c:
  assert c.get('/health').status_code==200
  email=f"smoke-{uuid.uuid4().hex[:10]}@example.com"
  payload={'name':'Smoke Auditor','email':email,'password':'StrongPass1','confirm_password':'StrongPass1','department':'Audit','employee_id':''}
  assert c.post('/auth/register',json=payload).status_code==200
  assert c.post('/auth/register',json=payload).status_code==409
  login=c.post('/auth/login',json={'username':email,'password':'StrongPass1'}); assert login.status_code==200
  h={'Authorization':'Bearer '+login.json()['access_token']}
  opts=c.get('/dashboard/options',headers=h).json(); assert opts['min_date']<=opts['max_date']
  result=c.get('/transactions?page_size=50',headers=h).json(); assert len(result['items'])<=50 and result['total']>0
  tx=result['items'][0]; opened=c.post(f"/cases/{tx['purchase_id']}/open",headers=h); assert opened.status_code==200
  case=opened.json(); cid=case['case']['case_id']; ev=case['evidence'][0]
  assert c.patch(f"/cases/{cid}/evidence/{ev['id']}",headers=h,json={'status':'Verified','comment':'Smoke test'}).status_code==200
  assert c.post(f"/cases/{cid}/notes",headers=h,json={'content':'Smoke note','important':False,'note_type':'Investigation Observation'}).status_code==200
  assert c.get(f"/cases/{cid}/report",headers=h).status_code==200
  assert c.get(f"/suppliers/{tx['vendor_id']}",headers=h).status_code==200
  assert c.post('/auth/logout',headers=h).status_code==200
  assert c.get('/cases',headers=h).status_code==401
 print('VendorShield smoke test passed')
if __name__=='__main__': run()

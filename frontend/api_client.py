from __future__ import annotations
import os
from typing import Any
import requests
DEFAULT_API_URL=os.environ.get('VENDORSHIELD_API_URL','http://127.0.0.1:8000').rstrip('/')
class APIError(RuntimeError): pass
class VendorShieldAPI:
 def __init__(self,base_url=DEFAULT_API_URL,timeout=60): self.base_url=base_url.rstrip('/'); self.timeout=timeout; self.session=requests.Session()
 def req(self,m,p,token=None,params=None,json=None,files=None,raw=False):
  try:r=self.session.request(m,self.base_url+p,headers={'Authorization':f'Bearer {token}'} if token else {},params=params,json=json,files=files,timeout=self.timeout)
  except requests.RequestException as e: raise APIError(f'Backend is not reachable at {self.base_url}. Start VendorShield first.') from e
  if r.status_code==401:
   if p=='/auth/login':
    try: detail=r.json().get('detail','Invalid email/username or password.')
    except Exception: detail='Invalid email/username or password.'
    raise APIError(str(detail))
   raise APIError('Your session expired. Please sign in again.')
  if not r.ok:
   try:d=r.json().get('detail',r.text)
   except Exception:d=r.text
   raise APIError(str(d))
  return r.content if raw else r.json()
 def health(self): return self.req('GET','/health')
 def login(self,u,p): return self.req('POST','/auth/login',json={'username':u,'password':p})
 def register(self,p): return self.req('POST','/auth/register',json=p)
 def profile(self,t): return self.req('GET','/auth/profile',t)
 def options(self,t): return self.req('GET','/dashboard/options',t)
 def summary(self,t,p): return self.req('GET','/dashboard/summary',t,params=p)
 def transactions(self,t,p): return self.req('GET','/transactions',t,params=p)
 def transaction(self,t,pid): return self.req('GET',f'/transactions/{pid}',t)
 def derive(self,t,p): return self.req('POST','/assessments/derive',t,json=p)
 def save(self,t,p): return self.req('POST','/assessments/save',t,json=p)
 def extract_pdf(self,t,name,data): return self.req('POST','/assessments/extract-pdf',t,files={'file':(name,data,'application/pdf')})
 def open_case(self,t,pid): return self.req('POST',f'/cases/{pid}/open',t)
 def cases(self,t,status=None): return self.req('GET','/cases',t,params={'status':status} if status else None)
 def case(self,t,cid): return self.req('GET',f'/cases/{cid}',t)
 def update_case(self,t,cid,p): return self.req('PATCH',f'/cases/{cid}',t,json=p)
 def add_note(self,t,cid,p): return self.req('POST',f'/cases/{cid}/notes',t,json=p)
 def evidence(self,t,cid,i,p): return self.req('PATCH',f'/cases/{cid}/evidence/{i}',t,json=p)
 def report(self,t,cid): return self.req('GET',f'/cases/{cid}/report',t,raw=True)
 def supplier(self,t,vid): return self.req('GET',f'/suppliers/{vid}',t)

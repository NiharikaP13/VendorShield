from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class LoginRequest(BaseModel):
    username: str
    password: str
class LoginResponse(BaseModel):
    access_token: str; token_type: Literal['bearer']='bearer'; expires_in_seconds:int
    username:str; email:str=''; role:str; display_name:str; auditor_id:int
class RegisterRequest(BaseModel):
    name:str=Field(min_length=2,max_length=120); email:str; password:str; confirm_password:str
    department:str=''; employee_id:str=''
    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.confirm_password: raise ValueError('Passwords do not match.')
        return self
class ReviewUpdate(BaseModel):
    status: Literal['Pending','Assigned','In Review','Escalated','Cleared After Review','Confirmed Issue','Insufficient Evidence']
    priority: Literal['Low','Medium','High','Critical']='High'; due_date:str|None=None; final_decision:str=''; escalation_reason:str=''
class NoteCreate(BaseModel): content:str=Field(min_length=1,max_length=5000); important:bool=False; note_type:str='Investigation Observation'
class EvidenceUpdate(BaseModel): status:Literal['Pending','Verified','Unavailable']; comment:str=Field(default='',max_length=1000)
class TransactionBusinessInput(BaseModel):
    vendor_id:str=Field(min_length=2,max_length=50); vendor_name:str=Field(min_length=2,max_length=120)
    vendor_category:str; region:str; category_product:str; product_name:str
    unit_of_measure:Literal['pallet','kg','meter','unit','carton','litre','roll','box']
    payment_method:Literal['RTGS','Bank Transfer','Cheque','NEFT','UPI']
    quantity:int=Field(gt=0); unit_price:float=Field(gt=0); invoice_amount:float=Field(gt=0); payment_amount:float=Field(gt=0)
    purchase_date:str; invoice_date:str; payment_date:str; invoice_number:str; purchase_order_number:str=''
    standard_unit_price:float|None=None; requested_by:str='Manual Assessment'; approved_by:str='Pending Review'; source:Literal['Manual Assessment','PDF Assessment']='Manual Assessment'
class TransactionScoreInput(BaseModel):
    vendor_category:str; region:str; category_product:str
    unit_of_measure:Literal['pallet','kg','meter','unit','carton','litre','roll','box']
    payment_method:Literal['RTGS','Bank Transfer','Cheque','NEFT','UPI']
    standard_unit_price:float; quantity:int; unit_price:float; purchase_amount:float; invoice_amount:float; payment_amount:float
    days_to_pay:int; vendor_tenure_days_at_purchase:int; vendor_historical_avg_price:float; price_deviation_ratio:float
    days_purchase_to_invoice:int; days_invoice_to_payment:int; days_purchase_to_payment:int; invoice_purchase_pct_diff:float
    is_suspected_shell_vendor:Literal[0,1]; purchase_before_vendor_registration:Literal[0,1]; is_round_invoice:Literal[0,1]
    invoice_amount_round_1000:Literal[0,1]; invoice_amount_round_5000:Literal[0,1]; is_rushed_payment:Literal[0,1]
    model_config=ConfigDict(extra='forbid')
class NewAssessmentCreate(TransactionBusinessInput): pass

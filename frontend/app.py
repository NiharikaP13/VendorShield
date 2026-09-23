from __future__ import annotations
from datetime import date,datetime
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from frontend.api_client import VendorShieldAPI,APIError,DEFAULT_API_URL
from frontend.styles import APP_CSS
st.set_page_config(page_title='VendorShield',page_icon='🛡️',layout='wide',initial_sidebar_state='expanded'); st.markdown(APP_CSS,unsafe_allow_html=True)
RISK={'High':'#ef4444','Medium':'#f59e0b','Low':'#22c55e'}
def money(v): return f"₹{float(v or 0):,.0f}"
def api(): return VendorShieldAPI(st.session_state.get('api_url',DEFAULT_API_URL))
def token(): return st.session_state['access_token']
def hero(title,sub): st.markdown(f'<div class="vs-hero"><div class="vs-eyebrow">VENDORSHIELD</div><div class="vs-hero-title">{title}</div><div class="vs-hero-copy">{sub}</div></div>',unsafe_allow_html=True)
def error(e): st.error(str(e))
def render_system_derived_values(result: dict) -> None:
 model=result.get('model_inputs') or {}
 provenance=result.get('provenance') or {}
 historical_count=int(provenance.get('vendor_transaction_frequency') or 0)
 historical_price_source=str(provenance.get('vendor_historical_avg_price') or '')
 tenure_source=str(provenance.get('vendor_tenure_days_at_purchase') or '')
 has_historical_price='historical' in historical_price_source.lower()
 has_registration_history='historical' in tenure_source.lower()
 shared_signal=bool(int(model.get('is_suspected_shell_vendor') or 0))
 avg_invoice=float(provenance.get('vendor_average_invoice') or 0)
 portfolio_delay=float(
  provenance.get('portfolio_average_payment_delay',
  provenance.get('portfolio_median_payment_delay',0)) or 0
 )
 rows=[
  {
   'System-derived field':'Historical Average Unit Price',
   'Value':money(model.get('vendor_historical_avg_price')),
   'Source':'Previous vendor transactions' if has_historical_price else 'Entered standard unit price (historical data unavailable)',
   'Meaning':'Typical unit price previously recorded for this vendor. It is used to compare the current purchase price.'
  },
  {
   'System-derived field':'Vendor Tenure at Purchase',
   'Value':f"{int(model.get('vendor_tenure_days_at_purchase') or 0):,} days",
   'Source':'Vendor registration history' if has_registration_history else 'No earlier registration record; treated as a new supplier',
   'Meaning':'Number of days between vendor registration and the current purchase date.'
  },
  {
   'System-derived field':'Portfolio Average Payment Delay',
   'Value':f"{portfolio_delay:.0f} days" if portfolio_delay else 'Not enough historical data',
   'Source':'All available procurement payment records',
   'Meaning':'Typical invoice-to-payment time across the procurement portfolio.'
  },
  {
   'System-derived field':'Historical Transactions',
   'Value':f"{historical_count:,} transaction{'s' if historical_count != 1 else ''}" if historical_count else 'No previous transactions',
   'Source':'All available transactions for this vendor',
   'Meaning':'Number of vendor transactions available to support this assessment.'
  },
  {
   'System-derived field':'Average Invoice Amount',
   'Value':money(avg_invoice) if historical_count and avg_invoice else 'Not enough historical data',
   'Source':'Previous invoices for this vendor',
   'Meaning':'Average invoice value recorded across the vendor’s available transaction history.'
  },
  {
   'System-derived field':'Shared Identity Signal',
   'Value':'Possible match found — review required' if shared_signal else 'No shared identity detected',
   'Source':'Historical vendor identity records',
   'Meaning':'Checks whether identity information is linked with another supplier. This is an investigation signal, not proof of misconduct.'
  },
 ]
 with st.expander('View system-calculated values and data sources',expanded=False):
  st.caption('These values were calculated automatically or retrieved from historical records; they were not entered manually in this assessment.')
  st.dataframe(
   pd.DataFrame(rows),
   hide_index=True,
   use_container_width=True,
   column_config={
    'System-derived field':st.column_config.TextColumn('System-derived field',width='medium'),
    'Value':st.column_config.TextColumn('Value',width='medium'),
    'Source':st.column_config.TextColumn('Source',width='large'),
    'Meaning':st.column_config.TextColumn('Meaning',width='large'),
   },
  )
  if historical_count == 0:
   st.info('This supplier has no previous transactions in the available database. Vendor-specific historical fields therefore use the entered standard price or a new-supplier assumption where required.')
  if shared_signal:
   st.warning('A shared identity signal requires evidence review. It must not be treated as confirmed fraud on its own.')
  else:
   st.caption('No shared identity was detected in the available records. This does not guarantee that no relationship exists outside the current dataset.')
def logout():
 for k in list(st.session_state):
  if k not in {'api_url'}: st.session_state.pop(k,None)
 st.rerun()
def auth_page():
 st.markdown('<div class="vs-auth-spacer"></div>',unsafe_allow_html=True)
 left,right=st.columns([1.08,.92],gap='large')
 with left:
  st.markdown('''<section class="vs-auth-intro">
    <div class="vs-auth-brand-row">
      <div class="vs-auth-logo">VS</div>
      <div>
        <div class="vs-auth-brand">VENDORSHIELD</div>
        <div class="vs-auth-brand-sub">PROCUREMENT RISK INTELLIGENCE</div>
      </div>
    </div>
    <div class="vs-auth-kicker">SECURE AUDITOR WORKSPACE</div>
    <h1>Procurement Risk Intelligence for Auditors</h1>
    <p class="vs-auth-lead">Review procurement transactions, identify suspicious supplier activity, understand explainable risk indicators, and document audit decisions from one secure workspace.</p>
    <div class="vs-auth-feature-grid">
      <div class="vs-auth-feature">
        <div class="vs-auth-feature-icon">AI</div>
        <div><strong>AI-Assisted Risk Screening</strong><span>Prioritises transactions and suppliers that may require closer review.</span></div>
      </div>
      <div class="vs-auth-feature">
        <div class="vs-auth-feature-icon">EX</div>
        <div><strong>Explainable Risk Indicators</strong><span>Shows clear business reasons behind each risk recommendation.</span></div>
      </div>
      <div class="vs-auth-feature">
        <div class="vs-auth-feature-icon">AR</div>
        <div><strong>Auditor-Led Case Review</strong><span>Keeps the final assessment, evidence review, and decision with the auditor.</span></div>
      </div>
    </div>
    <div class="vs-auth-flow-label">AUDIT WORKFLOW</div>
    <div class="vs-auth-flow">
      <span>Transaction Review</span><b>→</b><span>Risk Analysis</span><b>→</b><span>Evidence Check</span><b>→</b><span>Auditor Decision</span>
    </div>
    <div class="vs-auth-responsible">VendorShield supports investigation and prioritisation. It does not replace professional audit judgement.</div>
  </section>''',unsafe_allow_html=True)
 with right:
  with st.container(border=True,key='auth_form_card'):
   st.markdown('''<div class="vs-auth-form-head">
     <div class="vs-auth-kicker vs-auth-kicker-blue">PROTECTED ACCESS</div>
     <h2>Welcome back</h2>
     <p>Sign in to continue to your secure auditor workspace.</p>
   </div>''',unsafe_allow_html=True)
   tab1,tab2=st.tabs(['Sign In','Create Account'])
   with tab1:
    st.markdown('''<div class="vs-demo-box">
      <div><strong>Demo Auditor Access</strong><span>Use the verified demo account to explore the complete workflow.</span></div>
      <code>auditor1 / demo-password</code>
    </div>''',unsafe_allow_html=True)
    if st.button('Use Demo Credentials',use_container_width=True,key='fill_demo_credentials'):
     st.session_state['login_identifier']='auditor1'
     st.session_state['login_password']='demo-password'
     st.rerun()
    with st.form('signin'):
     u=st.text_input('Email or username',key='login_identifier',placeholder='Enter your email or auditor username')
     p=st.text_input('Password',type='password',key='login_password',placeholder='Enter your password')
     submit=st.form_submit_button('Sign In Securely',type='primary',use_container_width=True)
    if submit:
     try:
      r=api().login(u,p); st.session_state.update(r); st.rerun()
     except Exception as e:error(e)
   with tab2:
    st.caption('Create an individual auditor profile. Your activity and case decisions will remain separately attributed.')
    with st.form('signup'):
     name=st.text_input('Auditor name',placeholder='Full name')
     email=st.text_input('Email address',placeholder='name@organisation.com')
     dept=st.text_input('Department (optional)',placeholder='Internal Audit, Compliance, Finance...')
     emp=st.text_input('Employee ID (optional)',placeholder='Organisation employee ID')
     p1=st.text_input('Password',type='password',placeholder='Create a secure password')
     p2=st.text_input('Confirm password',type='password',placeholder='Re-enter the password')
     submit=st.form_submit_button('Create Auditor Account',type='primary',use_container_width=True)
    if submit:
     try:
      api().register({'name':name,'email':email,'department':dept,'employee_id':emp,'password':p1,'confirm_password':p2})
      st.success('Account created. Open the Sign In tab and use your email and password.')
     except Exception as e:error(e)
   st.markdown('''<div class="vs-auth-trust">
     <div><strong>Protected Session</strong><span>Authenticated access</span></div>
     <div><strong>Role-Based Access</strong><span>Individual profiles</span></div>
     <div><strong>Audit Logging</strong><span>Traceable activity</span></div>
   </div>''',unsafe_allow_html=True)
 st.markdown('''<footer class="vs-auth-footer">
   <span><strong>VendorShield</strong> — Procurement Risk Review Platform</span>
   <span>Secure access · Explainable analytics · Version 1.0</span>
 </footer>''',unsafe_allow_html=True)

def sidebar():
 st.sidebar.markdown('## 🛡️ VendorShield'); st.sidebar.caption(st.session_state.get('display_name','Auditor'))
 page=st.sidebar.radio('Workspace',['Command Center','Historical Procurement Portfolio','My Cases','Supplier Intelligence','＋ Assess New Transaction'])
 st.sidebar.divider();
 if st.sidebar.button('🚪 Logout',type='primary',use_container_width=True,key='logout_button'): logout()
 return page
def filter_controls(opts):
 st.sidebar.markdown('### Portfolio Filters'); search=st.sidebar.text_input('Search',placeholder='ID, vendor, invoice, PO, category, region')
 risks=st.sidebar.multiselect('Risk level',opts['risk_levels']); statuses=st.sidebar.multiselect('Review status',opts['review_statuses'])
 mode=st.sidebar.radio('Date range',['All Time','Custom Date Range'],horizontal=True)
 f={}
 if search:f['search']=search
 if risks:f['risk_level']=risks
 if statuses:f['review_status']=statuses
 if mode=='Custom Date Range':
  rng=st.sidebar.date_input('Dates',(datetime.fromisoformat(opts['min_date']).date(),datetime.fromisoformat(opts['max_date']).date()))
  if len(rng)==2:
   if rng[0]>rng[1]: st.sidebar.error('Start date must be before end date.')
   else:f.update(date_from=rng[0].isoformat(),date_to=rng[1].isoformat())
 with st.sidebar.expander('Advanced Filters'):
  regs=st.multiselect('Region',opts['regions']); cats=st.multiselect('Category',opts['categories']); shell=st.checkbox('Shared identity signals only')
  if regs:f['region']=regs
  if cats:f['category']=cats
  if shell:f['shell_only']=True
 chips=[]
 for k,v in f.items(): chips.append(f"{k}: {', '.join(v) if isinstance(v,list) else v}")
 st.sidebar.caption('Full portfolio' if not chips else 'Active Filters: '+' | '.join(chips))
 return f
def command_center(opts):
 f=filter_controls(opts)
 try:s=api().summary(token(),f)
 except Exception as e:error(e); return
 hero('Auditor Command Center','Operational procurement review, exposure monitoring, supplier intelligence, and case activity.')
 vals=[('High-Risk Review Queue',s['high_risk_count']),('Active Reviews',s['active_reviews']),('High-Risk Invoice Exposure',money(s['amount_at_risk'])),('Cases Due Today',0),('Escalated Cases',next((x['count'] for x in s['review_status_counts'] if x['review_status']=='Escalated'),0))]
 cols=st.columns(5)
 for col,(a,b) in zip(cols,vals): col.metric(a,b)
 st.info('High-Risk Invoice Exposure is the total invoice value associated with transactions recommended for review. It is not confirmed financial loss.')
 r=pd.DataFrame(s['risk_distribution']); tr=pd.DataFrame(s['fraud_trend']); v=pd.DataFrame(s['vendor_rollups']); cat=pd.DataFrame(s['category_rollups'])
 c1,c2=st.columns(2)
 with c1:
  if r.empty: st.info('No transactions match the selected filters. Reset the filters or expand the date range.')
  else: st.plotly_chart(px.pie(r,names='risk_level',values='count',hole=.55,color='risk_level',color_discrete_map=RISK,title='Risk distribution'),use_container_width=True)
 with c2:
  if not tr.empty: st.plotly_chart(px.line(tr,x='period',y=['High','Medium','Low'],title='Risk trend over time'),use_container_width=True)
 c1,c2=st.columns(2)
 with c1:
  if not v.empty: st.plotly_chart(px.bar(v.head(10),x='high_risk_count',y='vendor_name',orientation='h',title='Top risky suppliers'),use_container_width=True)
 with c2:
  if not cat.empty: st.plotly_chart(px.bar(cat,x='category',y='invoice_amount',title='Category-wise exposure'),use_container_width=True)
def portfolio(opts):
 f=filter_controls(opts); hero('Historical Procurement Portfolio','Shared historical and imported procurement records. New assessments remain separately attributed by source.')
 c1,c2,c3=st.columns([2,1,1]); search=c1.text_input('Global transaction search'); sort=c2.selectbox('Sort',['fraud_probability','invoice_amount','purchase_date','vendor_name']); order=c3.selectbox('Order',['desc','asc'])
 if search:f['search']=search
 try:r=api().transactions(token(),{**f,'page':1,'page_size':50,'sort_by':sort,'sort_order':order})
 except Exception as e:error(e); return
 df=pd.DataFrame(r['items'])
 if df.empty: st.warning('No transactions match the selected filters. Reset the filters or expand the date range.'); return
 st.caption(f"Showing 50 rows by default · {r['total']:,} matching records")
 st.dataframe(df,use_container_width=True,hide_index=True)
 ids=df['purchase_id'].tolist(); selected=st.selectbox('Select a transaction to open its case file',['']+ids)
 if not selected: st.info('Select a transaction from the review queue to open its case file.')
 elif st.button('Open Case File',type='primary'):
  try:b=api().open_case(token(),selected); st.session_state['case_id']=b['case']['case_id']; st.session_state['nav_override']='My Cases'; st.rerun()
  except Exception as e:error(e)
def case_view(bundle):
 cs=bundle['case']; t=bundle['transaction']; hero(f"Case File · {cs['case_id']}",f"{t.get('vendor_name')} · {t.get('invoice_number')}")
 if st.button('Back to Review Queue'): st.session_state.pop('case_id',None); st.session_state['nav_override']='Historical Procurement Portfolio'; st.rerun()
 c=st.columns(5); c[0].metric('Risk level',t.get('risk_level')); c[1].metric('Risk score',f"{float(t.get('fraud_probability') or 0)*100:.1f}%"); c[2].metric('Invoice',money(t.get('invoice_amount'))); c[3].metric('Status',cs['review_status']); c[4].metric('Priority',cs['priority'])
 st.markdown('### Business explanation'); st.write(f"Current unit price: {money(t.get('unit_price'))} · Supplier historical average: {money(t.get('vendor_historical_avg_price'))} · Deviation: {float(t.get('price_deviation_ratio') or 0):.2f}× · Invoice-to-payment: {t.get('days_invoice_to_payment')} days")
 st.markdown('#### Risk-Increasing Indicators')
 reasons=t.get('top_reasons',[]) or []
 if reasons:
  for reason in reasons:
   st.warning(str(reason))
 else:
  st.info('No strong increasing indicators returned.')
 st.markdown('#### Risk-Reducing Indicators'); st.success('Longer supplier tenure, price close to historical averages, normal payment timing, and verified evidence reduce concern when present.')
 with st.form('status'):
  status=st.selectbox('Review status',['Pending','Assigned','In Review','Escalated','Cleared After Review','Confirmed Issue','Insufficient Evidence'],index=['Pending','Assigned','In Review','Escalated','Cleared After Review','Confirmed Issue','Insufficient Evidence'].index(cs['review_status'])); priority=st.selectbox('Priority',['Low','Medium','High','Critical'],index=['Low','Medium','High','Critical'].index(cs['priority'])); due=st.date_input('Due date',datetime.fromisoformat(cs['due_date']).date() if cs.get('due_date') else date.today()); final=st.text_input('Final decision summary',cs.get('final_decision','')); reason=st.text_area('Escalation reason',cs.get('escalation_reason','')); ok=st.form_submit_button('Save Case Status',type='primary')
 if ok:
  try:api().update_case(token(),cs['case_id'],{'status':status,'priority':priority,'due_date':due.isoformat(),'final_decision':final,'escalation_reason':reason}); st.success('Case updated.'); st.rerun()
  except Exception as e:error(e)
 st.markdown('### Evidence Verification Checklist')
 for e in bundle['evidence']:
  with st.expander(e['item_name']):
   s=st.selectbox('Status',['Pending','Verified','Unavailable'],index=['Pending','Verified','Unavailable'].index(e['status']),key=f"es{e['id']}"); cm=st.text_input('Comment',e.get('comment',''),key=f"ec{e['id']}")
   if st.button('Save evidence',key=f"eb{e['id']}"):
    api().evidence(token(),cs['case_id'],e['id'],{'status':s,'comment':cm}); st.rerun()
 st.markdown('### Auditor Notes')
 with st.form('note'):
  nt=st.selectbox('Note type',['Investigation Observation','Escalation Reason','Final Audit Summary']); txt=st.text_area('Note'); important=st.checkbox('Mark important'); add=st.form_submit_button('Add Note')
 if add:
  try:api().add_note(token(),cs['case_id'],{'content':txt,'important':important,'note_type':nt}); st.rerun()
  except Exception as e:error(e)
 for n in bundle['notes']: st.write(f"{'⭐ ' if n['important'] else ''}**{n['author']} · {n['note_type']} · {n['created_at']}**\n\n{n['content']}")
 st.markdown('### Complete Audit Timeline')
 for x in bundle['timeline']: st.write(f"{x['created_at']} — **{x['action']}** — {x['auditor_name']} {x.get('comment','')}")
 try:pdf=api().report(token(),cs['case_id']); st.download_button('Download Case Report',pdf,file_name=f"{cs['case_id']}.pdf",mime='application/pdf',type='primary')
 except Exception as e:error(e)
 st.caption(bundle['disclaimer'])
def my_cases():
 if st.session_state.get('case_id'):
  try:case_view(api().case(token(),st.session_state['case_id']))
  except Exception as e:error(e)
  return
 hero('My Assigned Cases','Only cases assigned to the signed-in auditor are shown.')
 try:items=api().cases(token())['items']
 except Exception as e:error(e); return
 if not items: st.info('No assigned cases. Open a transaction from the review queue to create one.'); return
 df=pd.DataFrame(items); st.dataframe(df,use_container_width=True,hide_index=True); cid=st.selectbox('Open assigned case',['']+df['case_id'].tolist())
 if cid and st.button('Open Case File',type='primary'): st.session_state['case_id']=cid; st.rerun()
def suppliers(opts):
 hero('Supplier Intelligence','Vendor 360° profile, transaction history, risk movement, and neutral identity-signal review.')
 labels={f"{v['vendor_name']} · {v['vendor_id']}":v['vendor_id'] for v in opts['vendors']}; sel=st.selectbox('Select supplier',['']+list(labels))
 if not sel: st.info('Select a supplier to open the Vendor 360° profile.'); return
 try:p=api().supplier(token(),labels[sel])
 except Exception as e:error(e); return
 c=st.columns(5); c[0].metric('Transactions',p['total_transactions']); c[1].metric('Business value',money(p['total_business_value'])); c[2].metric('Average risk',f"{p['average_risk_score']*100:.1f}%"); c[3].metric('High-risk count',p['high_risk_count']); c[4].metric('Payment delay',f"{p['average_payment_delay']:.1f} days")
 st.write('Regions:',', '.join(p['regions'])); st.write('Categories:',', '.join(p['categories']))
 tr=pd.DataFrame(p['risk_trend']);
 if not tr.empty: st.plotly_chart(px.line(tr,x='period',y=['avg_risk','avg_price_deviation'],title='Risk and price deviation trend'),use_container_width=True)
 st.markdown('### Related Supplier Network'); st.warning(p['network_disclaimer']); st.info('No verified cross-supplier relationship records are available in the current dataset. The application does not fabricate links.')
 st.dataframe(pd.DataFrame(p['recent_transactions']),use_container_width=True,hide_index=True)
def assessment(opts):
 hero('＋ Assess New Transaction','Choose manual entry or upload a procurement PDF. No prediction runs until you review and submit valid details.')
 method=st.radio('Assessment method',['Manual Entry','Upload Procurement PDF'],horizontal=True,key='assessment_method')

 field_keys=['asm_vendor_id','asm_vendor_name','asm_product_name','asm_vendor_category','asm_region','asm_product_category','asm_unit','asm_quantity','asm_unit_price','asm_invoice_amount','asm_payment_amount','asm_payment_method','asm_invoice_number','asm_po_number','asm_purchase_date','asm_invoice_date','asm_payment_date']

 def parse_date_value(value):
  if not value:return None
  try:return datetime.fromisoformat(str(value).replace('/','-')).date()
  except Exception:return None

 def option_list(values,extracted_value=''):
  items=['']+list(values)
  if extracted_value and extracted_value not in items:items.insert(1,extracted_value)
  return items

 if method=='Upload Procurement PDF':
  up=st.file_uploader('Upload procurement PDF',type=['pdf'])
  if not up:
   st.info('No PDF uploaded.')
  elif st.button('Extract PDF Information',type='primary'):
   try:
    result=api().extract_pdf(token(),up.name,up.getvalue())
    extracted=result.get('fields',{})
    st.session_state['extracted']=extracted
    prefill={
     'asm_vendor_id':extracted.get('vendor_id',''),
     'asm_vendor_name':extracted.get('vendor_name',''),
     'asm_product_name':extracted.get('product_name',''),
     'asm_vendor_category':extracted.get('vendor_category',''),
     'asm_region':extracted.get('region',''),
     'asm_product_category':extracted.get('category_product',''),
     'asm_unit':extracted.get('unit_of_measure',''),
     'asm_quantity':int(extracted.get('quantity',0) or 0),
     'asm_unit_price':float(extracted.get('unit_price',0) or 0),
     'asm_invoice_amount':float(extracted.get('invoice_amount',0) or 0),
     'asm_payment_amount':float(extracted.get('payment_amount',0) or 0),
     'asm_payment_method':extracted.get('payment_method',''),
     'asm_invoice_number':extracted.get('invoice_number',''),
     'asm_po_number':extracted.get('purchase_order_number',''),
     'asm_purchase_date':parse_date_value(extracted.get('purchase_date')),
     'asm_invoice_date':parse_date_value(extracted.get('invoice_date')),
     'asm_payment_date':parse_date_value(extracted.get('payment_date')),
    }
    for key,value in prefill.items():st.session_state[key]=value
    st.session_state['pdf_extract_message']=result.get('message','PDF information extracted.')
    st.session_state['pdf_missing']=result.get('missing',[])
    st.rerun()
   except Exception as e:error(e)

 if st.session_state.get('pdf_extract_message') and method.startswith('Upload'):
  st.success(st.session_state['pdf_extract_message'])
  missing=st.session_state.get('pdf_missing',[])
  if missing:
   st.warning('Could not confidently extract: '+', '.join(missing)+'. Please enter or verify these fields manually.')
  else:
   st.info('All supported fields were extracted. Please verify them before assessment.')

 if st.button('Clear Form'):
  for key in field_keys:st.session_state.pop(key,None)
  for key in ['extracted','assessment_result','pdf_extract_message','pdf_missing']:st.session_state.pop(key,None)
  st.rerun()

 extracted=st.session_state.get('extracted',{}) if method.startswith('Upload') else {}
 vcat_options=option_list(opts['vendor_categories'],extracted.get('vendor_category',''))
 region_options=option_list(opts['regions'],extracted.get('region',''))
 cat_options=option_list(opts['categories'],extracted.get('category_product',''))
 unit_value=extracted.get('unit_of_measure','')
 if str(unit_value).lower()=='boxes':unit_value='box'
 unit_options=option_list(opts['units_of_measure'],unit_value)
 payment_value=extracted.get('payment_method','')
 if str(payment_value).lower().startswith('bank transfer'):payment_value='Bank Transfer'
 payment_options=option_list(opts['payment_methods'],payment_value)
 if 'asm_unit' in st.session_state and str(st.session_state['asm_unit']).lower()=='boxes':st.session_state['asm_unit']='box'
 if 'asm_payment_method' in st.session_state and str(st.session_state['asm_payment_method']).lower().startswith('bank transfer'):st.session_state['asm_payment_method']='Bank Transfer'

 with st.form('assessment_form'):
  c1,c2,c3=st.columns(3)
  vid=c1.text_input('Supplier ID',key='asm_vendor_id')
  vname=c2.text_input('Supplier name',key='asm_vendor_name')
  prod=c3.text_input('Product / category',key='asm_product_name')
  c1,c2,c3,c4=st.columns(4)
  vcat=c1.selectbox('Supplier category',vcat_options,key='asm_vendor_category')
  region=c2.selectbox('Region',region_options,key='asm_region')
  cat=c3.selectbox('Product category',cat_options,key='asm_product_category')
  unit=c4.selectbox('Unit',unit_options,key='asm_unit')
  c1,c2,c3=st.columns(3)
  qty=c1.number_input('Quantity',min_value=0,key='asm_quantity')
  price=c2.number_input('Unit price',min_value=0.0,key='asm_unit_price')
  invamt=c3.number_input('Invoice amount',min_value=0.0,key='asm_invoice_amount')
  c1,c2,c3=st.columns(3)
  payamt=c1.number_input('Payment amount',min_value=0.0,key='asm_payment_amount')
  methodp=c2.selectbox('Payment method',payment_options,key='asm_payment_method')
  invno=c3.text_input('Invoice number',key='asm_invoice_number')
  po=st.text_input('Purchase order number',key='asm_po_number')
  c1,c2,c3=st.columns(3)
  pdte=c1.date_input('Purchase date',value=None,key='asm_purchase_date')
  idte=c2.date_input('Invoice date',value=None,key='asm_invoice_date')
  paydte=c3.date_input('Payment date',value=None,key='asm_payment_date')
  submit=st.form_submit_button('Run Risk Assessment',type='primary',use_container_width=True)
 if submit:
  if not all([vid,vname,prod,vcat,region,cat,unit,methodp,invno,pdte,idte,paydte,qty,price,invamt,payamt]):
   st.error('Complete all required business fields before running the assessment.'); return
  b={'vendor_id':vid,'vendor_name':vname,'vendor_category':vcat,'region':region,'category_product':cat,'product_name':prod,'unit_of_measure':unit,'payment_method':methodp,'quantity':qty,'unit_price':price,'invoice_amount':invamt,'payment_amount':payamt,'purchase_date':pdte.isoformat(),'invoice_date':idte.isoformat(),'payment_date':paydte.isoformat(),'invoice_number':invno,'purchase_order_number':po,'standard_unit_price':None,'requested_by':'PDF Assessment' if method.startswith('Upload') else 'Manual Assessment','approved_by':'Pending Review','source':'PDF Assessment' if method.startswith('Upload') else 'Manual Assessment'}
  try:st.session_state['assessment_result']=api().derive(token(),b)
  except Exception as e:error(e)
 r=st.session_state.get('assessment_result')
 if r:
  pred=r['prediction']; st.success(f"{pred['risk_level']} risk recommendation · {pred['fraud_probability']*100:.2f}%")
  st.markdown('#### Risk-Increasing Indicators')
  reasons=pred.get('top_reasons',[]) or []
  if reasons:
   for reason in reasons:st.warning(str(reason))
  else:st.info('No strong increasing indicators returned.')
  st.markdown('#### System-derived values and data sources'); render_system_derived_values(r); st.caption(r['disclaimer'])
  if st.button('Save Assessment and Create Review Record',type='primary'):
   try:s=api().save(token(),r['business_inputs']); st.success(f"Saved as {s['purchase_id']}. Open it from the portfolio review queue.")
   except Exception as e:error(e)

def main():
 st.session_state.setdefault('api_url',DEFAULT_API_URL)
 if not st.session_state.get('access_token'): auth_page(); return
 try:opts=api().options(token())
 except Exception as e:error(e); return
 page=st.session_state.pop('nav_override',None) or sidebar()
 if page=='Command Center': command_center(opts)
 elif page=='Historical Procurement Portfolio': portfolio(opts)
 elif page=='My Cases': my_cases()
 elif page=='Supplier Intelligence': suppliers(opts)
 else: assessment(opts)
if __name__=='__main__': main()

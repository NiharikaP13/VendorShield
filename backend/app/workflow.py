from __future__ import annotations
import io, json, re, secrets, sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from backend.app import database, model_service

EVIDENCE_ITEMS=[
'Purchase order verified','Invoice copy verified','Approval hierarchy checked','Vendor bank account checked','Vendor tax information checked','Goods receipt confirmed','Price quotation verified','Quantity and invoice amount matched','Payment timeline reviewed','Supporting documents reviewed']
DISCLAIMER='The model output is a risk-prioritisation recommendation and does not independently establish fraud, misconduct, or financial loss. Final conclusions require human review and supporting evidence.'

def now()->str: return datetime.now(timezone.utc).isoformat()

def migrate()->None:
    with database.connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS auditors(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE COLLATE NOCASE, display_name TEXT NOT NULL, email TEXT UNIQUE COLLATE NOCASE NOT NULL, password_hash TEXT NOT NULL, department TEXT DEFAULT '', employee_id TEXT DEFAULT '', role TEXT NOT NULL DEFAULT 'auditor', created_at TEXT NOT NULL, last_login_at TEXT, is_demo INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, auditor_id INTEGER NOT NULL REFERENCES auditors(id) ON DELETE CASCADE, expires_at TEXT NOT NULL, created_at TEXT NOT NULL, revoked_at TEXT);
        CREATE TABLE IF NOT EXISTS cases(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT UNIQUE NOT NULL, purchase_id TEXT NOT NULL, assigned_auditor_id INTEGER REFERENCES auditors(id), priority TEXT NOT NULL DEFAULT 'High', due_date TEXT, review_status TEXT NOT NULL DEFAULT 'Assigned', final_decision TEXT DEFAULT '', escalation_reason TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(purchase_id,assigned_auditor_id));
        CREATE TABLE IF NOT EXISTS case_notes(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE, auditor_id INTEGER NOT NULL REFERENCES auditors(id), content TEXT NOT NULL, note_type TEXT NOT NULL, important INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS evidence_items(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE, item_name TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pending', comment TEXT DEFAULT '', updated_by INTEGER REFERENCES auditors(id), updated_at TEXT NOT NULL, UNIQUE(case_id,item_name));
        CREATE TABLE IF NOT EXISTS audit_timeline(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE, auditor_id INTEGER REFERENCES auditors(id), action TEXT NOT NULL, comment TEXT DEFAULT '', created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS saved_assessments(id INTEGER PRIMARY KEY AUTOINCREMENT, assessment_id TEXT UNIQUE NOT NULL, auditor_id INTEGER NOT NULL REFERENCES auditors(id), source TEXT NOT NULL, business_payload TEXT NOT NULL, model_payload TEXT NOT NULL, prediction TEXT NOT NULL, purchase_id TEXT, created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_cases_auditor ON cases(assigned_auditor_id,review_status);
        CREATE INDEX IF NOT EXISTS idx_timeline_case ON audit_timeline(case_id,created_at);
        CREATE INDEX IF NOT EXISTS idx_notes_case ON case_notes(case_id,created_at);
        CREATE INDEX IF NOT EXISTS idx_transactions_invoice ON transactions(invoice_number);
        CREATE INDEX IF NOT EXISTS idx_transactions_vendor_name ON transactions(vendor_name);
        ''')
        # Demo account. Hash generated locally without importing security (avoids cycle).
        if not c.execute("SELECT 1 FROM auditors WHERE username='auditor1'").fetchone():
            import hashlib
            salt=secrets.token_bytes(16); digest=hashlib.pbkdf2_hmac('sha256',b'demo-password',salt,210000)
            encoded=f'pbkdf2_sha256$210000${salt.hex()}${digest.hex()}'
            c.execute("INSERT INTO auditors(username,display_name,email,password_hash,department,employee_id,role,created_at,is_demo) VALUES(?,?,?,?,?,?,?,?,1)",('auditor1','Demo Procurement Auditor','auditor1@vendorshield.local',encoded,'Internal Audit','DEMO-001','auditor',now()))
        c.commit()

def rowdict(r): return dict(r) if r else None

def add_timeline(conn, case_pk:int, auditor_id:int|None, action:str, comment:str=''):
    conn.execute('INSERT INTO audit_timeline(case_id,auditor_id,action,comment,created_at) VALUES(?,?,?,?,?)',(case_pk,auditor_id,action,comment,now()))

def profile(auditor_id:int)->dict:
    with database.connect() as c:
        r=c.execute('SELECT id,username,display_name,email,department,employee_id,role,created_at,last_login_at,is_demo FROM auditors WHERE id=?',(auditor_id,)).fetchone(); return rowdict(r)

def create_or_open_case(purchase_id:str,auditor_id:int)->dict:
    if not database.transaction_detail(purchase_id): raise ValueError('Transaction not found.')
    with database.connect() as c:
        r=c.execute('SELECT * FROM cases WHERE purchase_id=? AND assigned_auditor_id=?',(purchase_id,auditor_id)).fetchone()
        if not r:
            case_id=f"CASE-{datetime.now():%Y%m%d}-{secrets.token_hex(3).upper()}"; ts=now(); due=(date.today()+timedelta(days=7)).isoformat()
            cur=c.execute('INSERT INTO cases(case_id,purchase_id,assigned_auditor_id,priority,due_date,review_status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',(case_id,purchase_id,auditor_id,'High',due,'Assigned',ts,ts)); pk=cur.lastrowid
            c.executemany('INSERT INTO evidence_items(case_id,item_name,status,updated_at) VALUES(?,?,?,?)',[(pk,x,'Pending',ts) for x in EVIDENCE_ITEMS])
            add_timeline(c,pk,auditor_id,'Case created','Created from transaction review queue'); add_timeline(c,pk,auditor_id,'Assigned to auditor','')
            c.commit(); r=c.execute('SELECT * FROM cases WHERE id=?',(pk,)).fetchone()
        else:
            add_timeline(c,r['id'],auditor_id,'Case opened',''); c.commit()
        return case_bundle(r['case_id'],auditor_id)

def case_bundle(case_id:str,auditor_id:int)->dict:
    with database.connect() as c:
        case=c.execute('''SELECT cs.*,a.display_name assigned_auditor,a.email assigned_email FROM cases cs LEFT JOIN auditors a ON a.id=cs.assigned_auditor_id WHERE cs.case_id=? AND cs.assigned_auditor_id=?''',(case_id,auditor_id)).fetchone()
        if not case: raise PermissionError('Case not found or not assigned to this auditor.')
        txn=database.transaction_detail(case['purchase_id']) or {}
        notes=[dict(x) for x in c.execute('''SELECT n.*,a.display_name author FROM case_notes n JOIN auditors a ON a.id=n.auditor_id WHERE n.case_id=? ORDER BY n.created_at DESC''',(case['id'],))]
        evidence=[dict(x) for x in c.execute('SELECT * FROM evidence_items WHERE case_id=? ORDER BY id',(case['id'],))]
        timeline=[dict(x) for x in c.execute('''SELECT t.*,COALESCE(a.display_name,'System') auditor_name FROM audit_timeline t LEFT JOIN auditors a ON a.id=t.auditor_id WHERE t.case_id=? ORDER BY t.created_at DESC''',(case['id'],))]
    return {'case':dict(case),'transaction':txn,'notes':notes,'evidence':evidence,'timeline':timeline,'disclaimer':DISCLAIMER}

def list_cases(auditor_id:int,status:str|None=None)->list[dict]:
    sql='''SELECT cs.case_id,cs.purchase_id,cs.priority,cs.due_date,cs.review_status,cs.final_decision,cs.updated_at,t.vendor_name,t.invoice_number,t.invoice_amount,t.risk_level,t.fraud_probability FROM cases cs JOIN transactions t ON t.purchase_id=cs.purchase_id WHERE cs.assigned_auditor_id=?'''; p=[auditor_id]
    if status: sql+=' AND cs.review_status=?'; p.append(status)
    sql+=' ORDER BY cs.updated_at DESC'
    with database.connect() as c: return [dict(r) for r in c.execute(sql,p)]

def update_case(case_id:str,auditor_id:int,data:dict)->dict:
    with database.connect() as c:
        case=c.execute('SELECT * FROM cases WHERE case_id=? AND assigned_auditor_id=?',(case_id,auditor_id)).fetchone()
        if not case: raise PermissionError('Case not found or not assigned to this auditor.')
        old=case['review_status']; c.execute('UPDATE cases SET priority=?,due_date=?,review_status=?,final_decision=?,escalation_reason=?,updated_at=? WHERE id=?',(data['priority'],data.get('due_date'),data['status'],data.get('final_decision',''),data.get('escalation_reason',''),now(),case['id']))
        if old!=data['status']: add_timeline(c,case['id'],auditor_id,'Status changed',f"{old} → {data['status']}")
        if data.get('final_decision'): add_timeline(c,case['id'],auditor_id,'Final decision recorded',data['final_decision'])
        c.commit()
    return case_bundle(case_id,auditor_id)

def add_note(case_id:str,auditor_id:int,content:str,important:bool,note_type:str)->dict:
    with database.connect() as c:
        case=c.execute('SELECT id FROM cases WHERE case_id=? AND assigned_auditor_id=?',(case_id,auditor_id)).fetchone()
        if not case: raise PermissionError('Case not found.')
        ts=now(); cur=c.execute('INSERT INTO case_notes(case_id,auditor_id,content,note_type,important,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',(case['id'],auditor_id,content,note_type,int(important),ts,ts)); add_timeline(c,case['id'],auditor_id,'Notes added',note_type); c.commit()
        return rowdict(c.execute('SELECT * FROM case_notes WHERE id=?',(cur.lastrowid,)).fetchone())

def update_evidence(case_id:str,item_id:int,auditor_id:int,status:str,comment:str)->dict:
    with database.connect() as c:
        case=c.execute('SELECT id FROM cases WHERE case_id=? AND assigned_auditor_id=?',(case_id,auditor_id)).fetchone()
        if not case: raise PermissionError('Case not found.')
        c.execute('UPDATE evidence_items SET status=?,comment=?,updated_by=?,updated_at=? WHERE id=? AND case_id=?',(status,comment,auditor_id,now(),item_id,case['id'])); add_timeline(c,case['id'],auditor_id,'Evidence updated',f'{status}: {comment}'[:500]); c.commit()
    return case_bundle(case_id,auditor_id)

def derive_features(b:dict)->tuple[dict,dict]:
    pd=datetime.fromisoformat(b['purchase_date']).date(); inv=datetime.fromisoformat(b['invoice_date']).date(); pay=datetime.fromisoformat(b['payment_date']).date()
    if inv<pd: raise ValueError('Invoice date cannot be earlier than purchase date.')
    if pay<inv: raise ValueError('Payment date cannot be earlier than invoice date.')
    with database.connect() as c:
        hist=c.execute('''SELECT AVG(unit_price) avg_price,MIN(registration_date) registration_date,COUNT(*) frequency,AVG(days_invoice_to_payment) avg_delay,AVG(invoice_amount) avg_invoice FROM transactions WHERE vendor_id=?''',(b['vendor_id'],)).fetchone()
        portfolio=c.execute('SELECT AVG(days_invoice_to_payment) delay,AVG(vendor_tenure_days_at_purchase) tenure FROM transactions').fetchone()
        shared=c.execute('SELECT MAX(is_suspected_shell_vendor) s FROM transactions WHERE vendor_id=?',(b['vendor_id'],)).fetchone()['s'] or 0
    hist_price=float(hist['avg_price'] or b.get('standard_unit_price') or b['unit_price'])
    registration=datetime.fromisoformat(hist['registration_date']).date() if hist['registration_date'] else pd
    tenure=max(0,(pd-registration).days); purchase=float(b['quantity'])*float(b['unit_price']); invoice=float(b['invoice_amount'])
    model={
      'vendor_category':b['vendor_category'],'region':b['region'],'category_product':b['category_product'],'unit_of_measure':b['unit_of_measure'],'payment_method':b['payment_method'],
      'standard_unit_price':float(b.get('standard_unit_price') or hist_price),'quantity':int(b['quantity']),'unit_price':float(b['unit_price']),'purchase_amount':purchase,'invoice_amount':invoice,'payment_amount':float(b['payment_amount']),
      'days_to_pay':(pay-inv).days,'vendor_tenure_days_at_purchase':tenure,'vendor_historical_avg_price':hist_price,'price_deviation_ratio':min(float(b['unit_price'])/hist_price if hist_price else 1,28.19),
      'days_purchase_to_invoice':(inv-pd).days,'days_invoice_to_payment':(pay-inv).days,'days_purchase_to_payment':(pay-pd).days,'invoice_purchase_pct_diff':((invoice-purchase)/purchase*100 if purchase else 0),
      'is_suspected_shell_vendor':int(shared),'purchase_before_vendor_registration':int(pd<registration),'is_round_invoice':int(invoice%1000==0 or invoice%5000==0),'invoice_amount_round_1000':int(invoice%1000==0),'invoice_amount_round_5000':int(invoice%5000==0),'is_rushed_payment':int((pay-inv).days<=1)}
    provenance={'vendor_historical_avg_price':'Retrieved from historical records' if hist['avg_price'] else 'Calculated from entered standard price','vendor_tenure_days_at_purchase':'Retrieved from historical records' if hist['registration_date'] else 'Unavailable; treated as new supplier','portfolio_average_payment_delay':float(portfolio['delay'] or 0),'vendor_transaction_frequency':int(hist['frequency'] or 0),'vendor_average_invoice':float(hist['avg_invoice'] or 0),'shared_identity_signal':'Retrieved from historical records'}
    return model,provenance

def save_assessment(auditor_id:int,business:dict,model:dict,pred:dict)->dict:
    assessment_id=f"ASM-{datetime.now():%Y%m%d%H%M%S}-{secrets.token_hex(2).upper()}"
    payload={**model,**{k:business[k] for k in ['vendor_id','vendor_name','product_name','purchase_date','invoice_number','requested_by','approved_by']},'purchase_order_number':business.get('purchase_order_number','')}
    record=database.insert_assessment(payload,pred,str(auditor_id))
    with database.connect() as c:
        c.execute('INSERT INTO saved_assessments(assessment_id,auditor_id,source,business_payload,model_payload,prediction,purchase_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(assessment_id,auditor_id,business.get('source','Manual Assessment'),json.dumps(business),json.dumps(model),json.dumps(pred),record['purchase_id'],now())); c.commit()
    return {'assessment_id':assessment_id,**record}

def supplier_profile(vendor_id:str)->dict:
    with database.connect() as c:
        r=c.execute('''SELECT vendor_id,MAX(vendor_name) vendor_name,MAX(vendor_category) vendor_category,MIN(registration_date) registration_date,COUNT(*) total_transactions,SUM(invoice_amount) total_business_value,AVG(invoice_amount) average_transaction_value,SUM(risk_level='High') high_risk_count,SUM(risk_level='Medium') medium_risk_count,SUM(risk_level='Low') low_risk_count,AVG(fraud_probability) average_risk_score,AVG(price_deviation_ratio) average_price_deviation,AVG(days_invoice_to_payment) average_payment_delay,MAX(is_suspected_shell_vendor) shared_identity_signal,MAX(purchase_date) last_transaction_date FROM transactions WHERE vendor_id=? GROUP BY vendor_id''',(vendor_id,)).fetchone()
        if not r: raise ValueError('Supplier not found.')
        regions=[x[0] for x in c.execute('SELECT DISTINCT region FROM transactions WHERE vendor_id=?',(vendor_id,))]; cats=[x[0] for x in c.execute('SELECT DISTINCT category_product FROM transactions WHERE vendor_id=?',(vendor_id,))]
        trend=[dict(x) for x in c.execute("SELECT substr(purchase_date,1,7) period,AVG(fraud_probability) avg_risk,AVG(price_deviation_ratio) avg_price_deviation,COUNT(*) transactions FROM transactions WHERE vendor_id=? GROUP BY period ORDER BY period",(vendor_id,))]
        tx=[dict(x) for x in c.execute('SELECT purchase_id,purchase_date,invoice_number,invoice_amount,risk_level,fraud_probability FROM transactions WHERE vendor_id=? ORDER BY purchase_date DESC LIMIT 50',(vendor_id,))]
    return {**dict(r),'regions':regions,'categories':cats,'risk_trend':trend,'recent_transactions':tx,'related_suppliers':[],'network_disclaimer':'Shared identity information is an investigation signal and does not establish misconduct.'}

def extract_pdf(data:bytes)->dict:
    """Extract labelled procurement fields from a text-based PDF.

    Supports both ``Label: Value`` and table-like PDFs where the value appears
    on the next line. It never invents values that are not present in the PDF.
    """
    if not data:
        raise ValueError('The uploaded PDF is empty.')
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        text = '\n'.join((page.extract_text() or '') for page in reader.pages)
    except Exception as exc:
        raise ValueError('The PDF could not be read. Use a valid text-based PDF or enter details manually.') from exc

    if not text.strip():
        return {
            'fields': {},
            'missing': ['All fields'],
            'message': 'No readable text was found. The PDF may be scanned; please use manual entry.'
        }

    lines = [re.sub(r'\s+', ' ', line).strip() for line in text.splitlines() if line.strip()]

    aliases = {
        'vendor_id': {'supplier id', 'vendor id'},
        'vendor_name': {'supplier name', 'vendor name'},
        'vendor_category': {'supplier category', 'vendor category'},
        'region': {'region', 'location'},
        'product_name': {'product / category', 'product/category', 'product name', 'item description', 'description'},
        'category_product': {'product category', 'item category'},
        'unit_of_measure': {'unit', 'unit of measure', 'uom'},
        'quantity': {'quantity', 'qty'},
        'unit_price': {'unit price', 'rate', 'price per unit'},
        'invoice_number': {'invoice number', 'invoice no', 'invoice #'},
        'purchase_order_number': {'purchase order number', 'purchase order no', 'po number', 'po no', 'po #'},
        'invoice_amount': {'invoice amount', 'invoice total', 'grand total', 'total amount'},
        'payment_amount': {'payment amount', 'amount paid'},
        'payment_method': {'payment method', 'mode of payment'},
        'purchase_date': {'purchase date', 'po date'},
        'invoice_date': {'invoice date'},
        'payment_date': {'payment date', 'paid date'},
    }
    label_to_field = {alias: field for field, names in aliases.items() for alias in names}
    fields: dict[str, Any] = {}

    def canonical_label(value: str) -> str:
        value = value.strip().lower().rstrip(':#-').strip()
        return re.sub(r'\s+', ' ', value)

    # Parse exact label/value rows. This avoids mistaking headings such as
    # "Purchase Order & Invoice Summary" for an invoice number.
    for i, line in enumerate(lines):
        inline = re.match(r'^(.{2,40}?)[\s]*[:#-][\s]*(.+)$', line)
        if inline:
            label = canonical_label(inline.group(1))
            if label in label_to_field and inline.group(2).strip():
                fields[label_to_field[label]] = inline.group(2).strip()
                continue

        label = canonical_label(line)
        if label in label_to_field and i + 1 < len(lines):
            next_value = lines[i + 1].strip()
            if canonical_label(next_value) not in label_to_field:
                fields[label_to_field[label]] = next_value

    # Anchored fallback for PDFs that place label and value on one line without punctuation.
    for field, names in aliases.items():
        if field in fields:
            continue
        for name in sorted(names, key=len, reverse=True):
            pattern = rf'(?im)^\s*{re.escape(name)}\s+(.+?)\s*$'
            match = re.search(pattern, text)
            if match:
                fields[field] = match.group(1).strip()
                break

    def parse_number(value: Any) -> float:
        cleaned = re.sub(r'[^0-9.\-]', '', str(value))
        if not cleaned or cleaned in {'-', '.', '-.'}:
            raise ValueError
        return float(cleaned)

    for key in ('quantity', 'unit_price', 'invoice_amount', 'payment_amount'):
        if key in fields:
            try:
                number = parse_number(fields[key])
                fields[key] = int(number) if key == 'quantity' and number.is_integer() else number
            except ValueError:
                fields.pop(key, None)

    for key in ('purchase_date', 'invoice_date', 'payment_date'):
        if key in fields:
            value = str(fields[key]).strip().replace('.', '/').replace('-', '/')
            match = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', value)
            if match:
                y, m, d = map(int, match.groups())
                try:
                    fields[key] = date(y, m, d).isoformat()
                except ValueError:
                    fields.pop(key, None)
            else:
                fields.pop(key, None)

    expected = [
        'vendor_id', 'vendor_name', 'vendor_category', 'region', 'product_name',
        'category_product', 'unit_of_measure', 'quantity', 'unit_price',
        'invoice_number', 'purchase_order_number', 'invoice_amount',
        'payment_amount', 'payment_method', 'purchase_date', 'invoice_date',
        'payment_date'
    ]
    display_names = {
        'vendor_id': 'Supplier ID', 'vendor_name': 'Supplier name',
        'vendor_category': 'Supplier category', 'region': 'Region',
        'product_name': 'Product / category', 'category_product': 'Product category',
        'unit_of_measure': 'Unit', 'quantity': 'Quantity', 'unit_price': 'Unit price',
        'invoice_number': 'Invoice number', 'purchase_order_number': 'Purchase order number',
        'invoice_amount': 'Invoice amount', 'payment_amount': 'Payment amount',
        'payment_method': 'Payment method', 'purchase_date': 'Purchase date',
        'invoice_date': 'Invoice date', 'payment_date': 'Payment date'
    }
    missing = [display_names[key] for key in expected if key not in fields]
    return {
        'fields': fields,
        'missing': missing,
        'message': 'PDF information extracted. Please verify every value before running the assessment.',
        'text_preview': text[:2000]
    }

def case_report(case_id:str,auditor_id:int)->bytes:
    b=case_bundle(case_id,auditor_id); case=b['case']; t=b['transaction']
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    out=io.BytesIO(); doc=SimpleDocTemplate(out,pagesize=A4,rightMargin=36,leftMargin=36,topMargin=36,bottomMargin=36); s=getSampleStyleSheet(); story=[Paragraph('VendorShield Case Report',s['Title']),Paragraph(DISCLAIMER,s['BodyText']),Spacer(1,12)]
    rows=[['Case ID',case['case_id']],['Transaction ID',case['purchase_id']],['Assigned auditor',case.get('assigned_auditor','')],['Review status',case['review_status']],['Final decision',case.get('final_decision') or 'Not recorded'],['Supplier',f"{t.get('vendor_name','')} ({t.get('vendor_id','')})"],['Invoice',t.get('invoice_number','')],['Invoice value',f"INR {float(t.get('invoice_amount') or 0):,.2f}"],['Risk level',t.get('risk_level','')],['Risk score',f"{float(t.get('fraud_probability') or 0)*100:.2f}%"]]
    table=Table(rows,colWidths=[150,350]); table.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#E2E8F0')),('GRID',(0,0),(-1,-1),.5,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP'),('PADDING',(0,0),(-1,-1),6)])); story+=[table,Spacer(1,14),Paragraph('Evidence checklist',s['Heading2'])]
    erows=[['Item','Status','Comment']]+[[e['item_name'],e['status'],e.get('comment','')] for e in b['evidence']]; et=Table(erows,colWidths=[220,80,200]); et.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#0F172A')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.4,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP'),('FONTSIZE',(0,0),(-1,-1),8)])); story+=[et,Spacer(1,14),Paragraph('Auditor notes',s['Heading2'])]
    for n in b['notes']: story.append(Paragraph(f"<b>{n['author']} · {n['created_at']}</b><br/>{n['content']}",s['BodyText']))
    story+=[Spacer(1,14),Paragraph('Audit timeline',s['Heading2'])]
    for x in reversed(b['timeline']): story.append(Paragraph(f"{x['created_at']} — <b>{x['action']}</b> — {x['auditor_name']} {x.get('comment','')}",s['BodyText']))
    doc.build(story); return out.getvalue()

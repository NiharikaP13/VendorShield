# VendorShield

**AI-Powered Procurement Risk Prioritisation, Supplier Intelligence, and Audit Case Management Platform**

VendorShield is a FastAPI + Streamlit application for procurement auditors. It combines a preserved XGBoost scoring pipeline with manual/PDF transaction assessment, supplier analytics, evidence-based case review, auditor notes, persistent audit timelines, and downloadable case reports.

> The model output is a risk-prioritisation recommendation and does not independently establish fraud, misconduct, or financial loss. Final conclusions require human review and supporting evidence.

## Business problem

Large procurement portfolios are difficult to review transaction by transaction. VendorShield helps auditors prioritise unusual records, compare them with supplier history, document evidence, and keep the ML recommendation separate from the auditor’s final decision.

## Main features

- Database-backed Sign Up, Sign In, Logout-ready sessions, PBKDF2 password hashing, duplicate-email checks, and separate auditor profiles.
- Command Center with database-derived historical dates, High-Risk Review Queue, Active Reviews, High-Risk Invoice Exposure, trends, supplier concentration, and category exposure.
- Historical Procurement Portfolio with search, filters, sorting, and server-side 50-row pagination.
- Blank-by-default manual assessment form and optional procurement-PDF extraction.
- Automatic derivation of model-engineered inputs from entered dates and historical supplier records.
- Auditor-specific cases, professional review statuses, priorities, due dates, evidence checklist, notes, and persistent timeline.
- Vendor 360° profile with transaction, exposure, risk, price-deviation, and payment-behaviour summaries.
- Professional PDF case report with evidence, notes, timeline, and model disclaimer.

## Auditor workflow

1. Register or sign in.
2. Review the Command Center.
3. Search the Historical Procurement Portfolio.
4. Select a transaction and explicitly open a case file.
5. Verify evidence, add notes, and update review status.
6. Open Supplier Intelligence for supplier context.
7. Run a manual or PDF-based assessment.
8. Save the assessment only after review.
9. Download the case report.

## System architecture

```text
Streamlit Frontend
       │ HTTP + Bearer session
       ▼
FastAPI Backend
 ├─ Authentication and auditor access control
 ├─ Dashboard/query services
 ├─ Assessment feature derivation
 ├─ Preserved XGBoost model service
 ├─ Case, evidence, notes, timeline services
 ├─ PDF extraction and report generation
       │
       ▼
Indexed SQLite Database + saved model artifacts
```

## Technology stack

- Python 3.11+
- Streamlit
- FastAPI / Uvicorn
- SQLite
- XGBoost, scikit-learn, SHAP, joblib
- Plotly, pandas, NumPy
- pypdf for text-based PDF extraction
- ReportLab for PDF case reports

## Important folders

```text
backend/app/       API, security, database, model and workflow services
backend/model/     preserved trained model and model metadata
frontend/          Streamlit application, styles and API client
data/              procurement database
scripts/           database/data preparation scripts
tests/             smoke tests
```

## Machine-learning integrity

The saved model file, preprocessing pipeline, feature order, thresholds, and risk mapping are not retrained or randomly changed by the application upgrade. Business inputs are converted into the existing required feature structure by the backend. New assessments are tagged separately and are not automatically used as training data.

## Authentication workflow

Passwords are stored as salted PBKDF2-SHA256 hashes. Sessions are persisted in the database with expiry timestamps. Cases, notes, activity, evidence, and saved assessments are scoped to the signed-in auditor.

Demo account:

Demo account credentials are provided separately for demonstration purposes.

Registered users sign in with their email address or generated username.

## PDF assessment workflow

1. Select **Upload Procurement PDF**.
2. Upload a text-based PDF up to 10 MB.
3. Extract available invoice, PO, supplier, quantity, price, and amount fields.
4. Review missing/uncertain fields and edit all values.
5. Submit only after verification.

Scanned PDFs without embedded text are not fabricated or guessed; use manual entry for those documents.

## Database setup

The supplied database already contains the historical portfolio. On startup, VendorShield safely creates only missing workflow tables and indexes. It does not delete or overwrite historical procurement data.

To rebuild the original historical database only when intentionally required:

```bash
python scripts/build_database.py
```

## Automatic Run

### Windows

```bat
run_vendorshield.bat
```

### macOS/Linux

```bash
chmod +x run_vendorshield.sh
./run_vendorshield.sh
```

## Manual Run

### 1. Open the project folder

```bash
cd VendorShield_Professional_Project_Final
```

### 2. Create and activate an environment

```bash
conda create -n vendorshield python=3.11 -y
conda activate vendorshield
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

On Windows, copy `.env.example` to `.env` using File Explorer or:

```bat
copy .env.example .env
```

### 5. Start the backend

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### 6. Start the frontend in a second terminal

```bash
python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

Open `http://127.0.0.1:8501`.

Stop each service with `Ctrl+C`.

## Common errors

- **Backend not reachable:** start Uvicorn before Streamlit and confirm port 8000 is free.
- **Database missing:** run `python scripts/build_database.py` only if `data/vendorshield.db` is absent.
- **Model loading failure:** reinstall exact dependencies from `requirements.txt`; do not replace the model file.
- **Scanned PDF:** use manual entry because OCR is not enabled in this build.
- **Session expired:** sign in again.
- **No chart results:** reset filters or use **All Time**; the default database range is 2022-01-01 to 2025-12-30 in the supplied dataset.

## Performance notes

The model and dashboard aggregates warm in the background, common summaries are cached, queries use SQLite indexes, and transaction tables request 50 rows by default. Detailed explanations are calculated when a transaction is opened or assessed.

## Security notes

This academic application implements password hashing, session expiry, protected API routes, parameterised SQLite queries, duplicate-account checks, PDF type/size validation, and auditor-specific case access. Production deployment would still require HTTPS, a managed secrets service, stronger operational monitoring, backups, rate limiting, and formal security testing.

## Future improvements

- OCR for scanned invoices.
- Managed PostgreSQL and enterprise SSO.
- Audit-manager role and reassignment approvals.
- Verified supplier master-data relationships for an interactive network graph.
- Controlled model retraining and model-governance workflow.


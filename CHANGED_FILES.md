# Changed Files

- `backend/app/security.py` — hashed-password authentication, registration, persistent sessions, expiry, logout revocation.
- `backend/app/schemas.py` — registration, business assessment, professional case status, notes, and evidence schemas.
- `backend/app/workflow.py` — database migration, auditor cases, evidence, notes, timeline, feature derivation, PDF extraction, supplier profile, and PDF report generation.
- `backend/app/database.py` — auditor/session helpers, source and PO support, expanded global search, updated status options.
- `backend/app/main.py` — protected authentication, assessment, PDF, case, supplier, and report endpoints.
- `frontend/api_client.py` — client methods for all upgraded API workflows.
- `frontend/app.py` — redesigned multi-auditor UI, blank assessment, explicit case opening, Command Center, cases, evidence, notes, timeline, supplier profile, and PDF downloads.
- `requirements.txt` — PDF upload/extraction/report dependencies.
- `.env.example` — environment configuration without personal paths or secrets.
- `run_vendorshield.bat` and `run_vendorshield.sh` — safe automatic startup scripts.
- `README.md` — professional architecture, workflows, setup, run, security, performance, and limitation documentation.
- `tests/smoke_test.py` — end-to-end backend smoke test.
- `TESTING_SUMMARY.md` — completed checks and unautomated limitations.

## Login hotfix
- `frontend/app.py`: aligned Streamlit session handling with the backend `access_token` response field.
- `frontend/api_client.py`: preserves invalid-login messages instead of reporting every HTTP 401 as an expired session.

## PDF extraction correction
- `backend/app/workflow.py`: Added label-aware next-line and inline procurement PDF extraction, numeric/date normalisation, and false-heading protection.
- `frontend/app.py`: Added complete PDF field prefilling, friendly missing-field messages, explicit widget state, date/select prefilling, and clear-form reset.
- `sample_documents/sample_procurement_transaction.pdf`: Added a text-based sample for testing.

## Login page enhancement
- `frontend/app.py`: Rebuilt the authentication page as a balanced two-column experience with a product introduction, feature explanations, audit workflow, secure sign-in card, one-click demo credential filling, clearer registration guidance, trust indicators, and footer.
- `frontend/styles.py`: Added responsive authentication-page styling, professional dark-gradient branding, form-card treatment, feature panels, demo-access panel, trust cards, and mobile layout rules.

## System-derived values display update (2026-08-04)

- Replaced the raw provenance JSON on the New Assessment result with a collapsed, auditor-friendly table.
- Added separate **Value**, **Source**, and **Meaning** columns.
- Formatted currency, day counts, transaction counts, and shared-identity status in readable business language.
- Added clear handling for suppliers with insufficient historical data.
- Added a warning that shared identity is an investigation signal, not proof of fraud.
- Corrected the payment-delay label from “median” to “average” because the backend calculation uses SQL `AVG`.

Files updated:
- `frontend/app.py`
- `backend/app/workflow.py`

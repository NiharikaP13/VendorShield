# Testing Summary

Validated on the packaged project using FastAPI TestClient and Python compilation.

## Passed checks

- API health and database availability.
- New auditor registration.
- Duplicate email rejection (HTTP 409).
- Correct login and demo login.
- Database-derived date range: 2022-01-01 to 2025-12-30.
- Server-side transaction page returns 50 rows.
- Explicit case creation/opening.
- Auditor-specific case retrieval.
- Evidence update persistence.
- Auditor note persistence.
- Audit timeline creation.
- Supplier 360° endpoint.
- PDF case report generation.
- Unsupported PDF/file rejection.
- Business-input feature derivation and model prediction.
- Python compilation of backend, frontend, scripts, and tests.

## Not fully automated in this environment

- Browser-level visual regression and mobile layout testing.
- OCR extraction from scanned PDFs (not implemented).
- Multi-browser concurrent session UI testing.
- Real supplier network interaction because the supplied portfolio does not include verified shared bank/tax/address identifiers between named suppliers.

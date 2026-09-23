# VendorShield Build Validation

Validated on 2 August 2026.

## Verified components

- Python source compilation
- FastAPI application import
- Auditor authentication
- 60,000-row reconstructed held-out historical portfolio
- Dashboard filters and summary calculations
- Paginated transaction review queue
- Transaction case retrieval
- Plain-language local risk explanations
- Persistent review status and auditor notes
- New transaction risk scoring
- Saving and reopening a new assessment
- One-click Windows launcher

## Smoke-test result

All checks in `tests/smoke_test.py` passed successfully.

## Data separation

The source dataset contains 300,000 records. The dashboard database uses a stable stratified 20% reconstruction of the held-out portfolio, while the model-development rows are not displayed as the operational review queue.

# PDF Extraction Fix

The procurement PDF extractor now supports both inline fields such as `Invoice Number: INV-001` and table-style PDFs where each value appears on the line after its label.

Supported fields include supplier, product, quantity, unit price, invoice/payment values, payment method, purchase order, and transaction dates.

The New Assessment form is populated only with values actually found in the uploaded PDF. Every extracted value remains editable and must be verified before risk assessment.

Use `sample_documents/sample_procurement_transaction.pdf` to test the workflow.

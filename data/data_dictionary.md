# VendorShield — Data Dictionary (Part 1: Data Generation)

## Overview

This synthetic dataset simulates a company's procurement-to-pay cycle across
five relational tables: **vendors, products, purchases, invoices, payments**.
It was generated with `generate_data.py` (seed = 42, fully reproducible) and
is intended to stand in for real procurement data, which companies do not
publish due to confidentiality.

| Table | Rows | Grain |
|---|---|---|
| vendors.csv | 3,200 | one row per vendor |
| products.csv | 220 | one row per product/SKU |
| purchases.csv | 300,000 | one row per purchase order |
| invoices.csv | 300,000 | one row per invoice (1:1 with purchases) |
| payments.csv | 300,000 | one row per payment (1:1 with invoices) |

Overall fraud rate in `purchases.csv`: **~6.9%** of transactions.

---

## 1. vendors.csv

| Column | Type | Description |
|---|---|---|
| vendor_id | string | Unique vendor identifier (e.g. `V100427`) |
| vendor_name | string | Vendor's registered business name |
| category | string | Vendor's primary supply category |
| region | string | City/region the vendor operates from |
| bank_account_number | string | Bank account used for payouts |
| tax_id | string | GST-style tax identifier |
| registration_date | date | Date the vendor was onboarded |
| shell_cluster_id | float (nullable) | Reference field only. If not null, this vendor shares a `bank_account_number` and/or `tax_id` with 1-3 other vendors under a **different vendor name** — simulating a shell-vendor / duplicate-vendor fraud ring. ~5% of vendors (160) belong to a cluster. **This column is provided for validation/EDA purposes in Part 2, not as a purchase-level fraud feature.** |

## 2. products.csv

| Column | Type | Description |
|---|---|---|
| product_id | string | Unique product identifier |
| product_name | string | Descriptive product name |
| category | string | Product category |
| unit_of_measure | string | Unit the product is purchased in (kg, box, litre, etc.) |
| standard_unit_price | float | Reference/list price for the product, before vendor-specific pricing variation |

## 3. purchases.csv  — the fraud-labeled table

| Column | Type | Description |
|---|---|---|
| purchase_id | string | Unique purchase order id |
| vendor_id | string | FK → vendors.vendor_id |
| product_id | string | FK → products.product_id |
| requested_by | string | Employee id who raised the purchase |
| purchase_date | date | Date the purchase order was raised |
| quantity | int | Quantity ordered |
| unit_price | float | Actual unit price paid on this order |
| purchase_amount | float | quantity × unit_price |
| **fraud_label** | int (0/1) | 1 if this transaction was flagged as fraudulent during generation |
| **fraud_reason** | string | Semicolon-separated list of the fraud pattern(s) injected (see below). Empty for clean rows. |

### Fraud injection logic

~7% of purchase rows were deliberately flagged and modified using one or two
of the following patterns (70% of fraud rows get a single pattern, 30% get two
combined):

1. **price_inflation** — unit price inflated 1.4×–2.8× above the vendor's
   normal historical average for that product.
2. **invoice_mismatch** — the resulting invoice amount is altered 8%–40%
   away from the true purchase amount (see invoices.csv).
3. **round_number_invoice** — the invoice amount is forced to a suspiciously
   round figure (nearest ₹1,000 or ₹5,000) rather than a natural computed value.
4. **rushed_payment** — the payment is approved same-day or next-day instead
   of the normal 5-30 day cycle (see payments.csv).

**No label leakage / realistic overlap:** to prevent the label from being
trivially predictable from a single feature, a small share of *non-fraud*
transactions were also given legitimate premium pricing (~1.5%), natural
invoice rounding noise (~3% of clean invoices), and legitimate urgent-payment
rushes (~1% of clean payments). Every fraud row has a non-empty
`fraud_reason`; every clean row has an empty `fraud_reason` — there is no
partial or ambiguous labeling.

## 4. invoices.csv

| Column | Type | Description |
|---|---|---|
| invoice_id | string | Unique invoice id |
| purchase_id | string | FK → purchases.purchase_id |
| vendor_id | string | FK → vendors.vendor_id |
| invoice_date | date | Date invoice was raised (0-9 days after purchase_date) |
| invoice_number | string | Vendor-issued invoice number |
| invoice_amount | float | Amount invoiced. Equal to purchase_amount unless the transaction carries `invoice_mismatch` and/or `round_number_invoice` |

## 5. payments.csv

| Column | Type | Description |
|---|---|---|
| payment_id | string | Unique payment id |
| invoice_id | string | FK → invoices.invoice_id |
| vendor_id | string | FK → vendors.vendor_id |
| payment_date | date | invoice_date + days_to_pay |
| payment_amount | float | Amount paid (settles invoice_amount) |
| payment_method | string | Bank Transfer / Cheque / NEFT / RTGS / UPI |
| approved_by | string | Employee id who approved payment |
| days_to_pay | int | Days between invoice_date and payment_date. Normally 5-30 days; 0-1 days when `rushed_payment` was injected |

---

## Relational keys

```
vendors (vendor_id) ─┬─< purchases (vendor_id, product_id) >─ products
                      ├─< invoices (vendor_id, purchase_id → purchases)
                      └─< payments (vendor_id, invoice_id → invoices)
```

- `purchases.purchase_id` ↔ `invoices.purchase_id` is 1:1
- `invoices.invoice_id` ↔ `payments.invoice_id` is 1:1
- `vendors.bank_account_number` / `tax_id` can repeat across *different*
  `vendor_id`/`vendor_name` — this is the intentional shell-vendor signal for
  Part 2's duplicate-vendor detection.

## Reproducibility

The generator uses `numpy.random.default_rng(seed=42)` throughout. Re-running
`generate_data.py` unmodified will always reproduce the exact same five
files.

## Suggested next steps for Person 2

- Validate referential integrity across the five tables.
- Cluster vendors by `bank_account_number` / `tax_id` to surface the shell
  clusters independently of `shell_cluster_id` (treat that column as ground
  truth for validation only, not as a modeling feature to hand to Person 3).
- Explore fraud rate by category, region, vendor tenure, and payment method.

"""
VendorShield — Part 1: Synthetic Data Generator
=================================================

Generates a realistic, relational synthetic dataset for a procurement
fraud & supplier-risk analytics platform. No external identity library
(e.g. Faker) is used — name generation is done with curated word banks
so the script has zero third-party dependencies beyond numpy/pandas.

Tables produced (5), written to ./output/:
    vendors.csv
    products.csv
    purchases.csv
    invoices.csv
    payments.csv

Run:
    python generate_data.py

Reproducible: a fixed RNG seed is used throughout (see SEED below).
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
SEED = 42
rng = np.random.default_rng(SEED)

N_VENDORS = 3200
N_PRODUCTS = 220
N_PURCHASES = 300_000

FRAUD_RATE = 0.07          # ~7% of purchase transactions carry a fraud label
SHELL_CLUSTER_VENDOR_SHARE = 0.05   # ~5% of vendors sit inside a duplicate/shell cluster

DATE_START = datetime(2022, 1, 1)
DATE_END = datetime(2025, 12, 31)

OUT_DIR = "output"
os.makedirs(OUT_DIR, exist_ok=True)

# ----------------------------------------------------------------------
# NAME / WORD BANKS  (used instead of an external identity library)
# ----------------------------------------------------------------------
VENDOR_PREFIXES = [
    "Shri", "Global", "National", "United", "Prime", "Metro", "Om", "Sai",
    "Bharat", "Apex", "Everest", "Sunrise", "Continental", "Pinnacle", "Vertex",
    "Silverline", "Bluewave", "Crown", "Royal", "Alliance", "Trident", "Horizon",
    "Nova", "Falcon", "Zenith", "Unity", "Classic", "Modern", "Precision", "Reliable"
]
VENDOR_CORES = [
    "Steel", "Traders", "Enterprises", "Industries", "Suppliers", "Logistics",
    "Textiles", "Electronics", "Chemicals", "Packaging", "Foods", "Agro",
    "Hardware", "Components", "Plastics", "Engineering", "Construction",
    "Trading Co", "Distributors", "Solutions", "Exports", "Import Export",
    "Fabricators", "Machinery", "Automotive", "Paper Mills", "Pharma", "Metals"
]
VENDOR_SUFFIXES = ["Pvt Ltd", "Ltd", "LLP", "Corp", "Inc", "& Sons", "Co", "Group"]

PRODUCT_CATEGORIES = [
    "Raw Materials", "Office Supplies", "IT Equipment", "Packaging Materials",
    "Industrial Machinery", "Electrical Components", "Chemicals", "Textiles",
    "Construction Materials", "Logistics Services", "MRO Supplies", "Food & Beverage"
]
PRODUCT_ADJ = [
    "Standard", "Premium", "Heavy-Duty", "Industrial-Grade", "Bulk", "Compact",
    "High-Density", "Recycled", "Precision", "Commercial", "Wholesale", "Custom"
]
PRODUCT_NOUNS = [
    "Steel Sheets", "Copper Wire", "Cardboard Boxes", "Bubble Wrap", "Laptops",
    "Desktop Monitors", "Printer Cartridges", "A4 Paper Reams", "Industrial Bolts",
    "Ball Bearings", "Hydraulic Pumps", "Conveyor Belts", "PVC Pipes", "Cement Bags",
    "Cotton Fabric Rolls", "Polyester Yarn", "Circuit Boards", "LED Panels",
    "Diesel Generators", "Safety Helmets", "Work Gloves", "Chemical Solvents",
    "Lubricant Oil", "Plastic Pallets", "Wooden Crates", "Aluminium Rods",
    "Rubber Gaskets", "Office Chairs", "Filing Cabinets", "Network Switches"
]
UNITS = ["unit", "kg", "box", "litre", "roll", "meter", "carton", "pallet"]

REGIONS = [
    "Delhi NCR", "Mumbai", "Bengaluru", "Chennai", "Hyderabad", "Pune", "Kolkata",
    "Ahmedabad", "Jaipur", "Surat", "Noida", "Gurugram", "Coimbatore", "Nagpur"
]

EMPLOYEES = [f"EMP{100+i:04d}" for i in range(180)]   # requesting employees / approvers

# ----------------------------------------------------------------------
# 1. VENDORS
# ----------------------------------------------------------------------
def make_vendor_name(i):
    return f"{rng.choice(VENDOR_PREFIXES)} {rng.choice(VENDOR_CORES)} {rng.choice(VENDOR_SUFFIXES)} ({i})"

def random_date(start, end):
    delta = end - start
    return start + timedelta(days=int(rng.integers(0, delta.days)))

def gen_bank_account():
    return f"{rng.integers(10**11, 10**12 - 1)}"

def gen_tax_id():
    # loosely GST-style alphanumeric
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return (f"{rng.integers(10,99)}"
            f"{''.join(rng.choice(list(letters)) for _ in range(5))}"
            f"{rng.integers(1000,9999)}"
            f"{rng.choice(list(letters))}1Z{rng.integers(0,9)}")

vendor_ids = [f"V{100000+i}" for i in range(N_VENDORS)]
vendor_names, bank_accounts, tax_ids, regions, categories, reg_dates = [], [], [], [], [], []

# First generate a pool of unique bank accounts / tax ids
n_shell_vendors = int(N_VENDORS * SHELL_CLUSTER_VENDOR_SHARE)
n_unique_vendors = N_VENDORS - n_shell_vendors

unique_accounts = [gen_bank_account() for _ in range(n_unique_vendors)]
unique_tax_ids = [gen_tax_id() for _ in range(n_unique_vendors)]

# Build shell clusters: groups of 2-4 vendors sharing either the same bank account
# or the same tax id, but with different vendor names (classic shell-vendor pattern)
shell_cluster_id = []
cluster_counter = 0
remaining_shell = n_shell_vendors
cluster_assignments = {}  # vendor index -> (shared_account_or_None, shared_taxid_or_None, cluster_id)

idx = n_unique_vendors
while remaining_shell > 0:
    cluster_size = min(rng.integers(2, 5), remaining_shell)
    share_type = rng.choice(["account", "taxid", "both"])
    shared_account = gen_bank_account() if share_type in ("account", "both") else None
    shared_taxid = gen_tax_id() if share_type in ("taxid", "both") else None
    for _ in range(cluster_size):
        cluster_assignments[idx] = (shared_account, shared_taxid, cluster_counter)
        idx += 1
    remaining_shell -= cluster_size
    cluster_counter += 1

for i in range(N_VENDORS):
    vendor_names.append(make_vendor_name(i))
    categories.append(rng.choice(PRODUCT_CATEGORIES))
    regions.append(rng.choice(REGIONS))
    reg_dates.append(random_date(datetime(2015, 1, 1), datetime(2023, 12, 31)).date())

    if i < n_unique_vendors:
        bank_accounts.append(unique_accounts[i])
        tax_ids.append(unique_tax_ids[i])
        shell_cluster_id.append(np.nan)
    else:
        shared_account, shared_taxid, cid = cluster_assignments[i]
        bank_accounts.append(shared_account if shared_account else gen_bank_account())
        tax_ids.append(shared_taxid if shared_taxid else gen_tax_id())
        shell_cluster_id.append(cid)

vendors = pd.DataFrame({
    "vendor_id": vendor_ids,
    "vendor_name": vendor_names,
    "category": categories,
    "region": regions,
    "bank_account_number": bank_accounts,
    "tax_id": tax_ids,
    "registration_date": reg_dates,
    "shell_cluster_id": shell_cluster_id,   # NaN = not part of a duplicate cluster (research/reference field)
})

# Shuffle row order so shell-cluster vendors aren't all bunched at the end
vendors = vendors.sample(frac=1, random_state=SEED).reset_index(drop=True)

# ----------------------------------------------------------------------
# 2. PRODUCTS
# ----------------------------------------------------------------------
product_ids = [f"P{1000+i}" for i in range(N_PRODUCTS)]
prod_names, prod_cats, prod_units, prod_base_price = [], [], [], []
used_names = set()
for i in range(N_PRODUCTS):
    name = f"{rng.choice(PRODUCT_ADJ)} {rng.choice(PRODUCT_NOUNS)}"
    while name in used_names:
        name = f"{rng.choice(PRODUCT_ADJ)} {rng.choice(PRODUCT_NOUNS)}"
    used_names.add(name)
    prod_names.append(name)
    prod_cats.append(rng.choice(PRODUCT_CATEGORIES))
    prod_units.append(rng.choice(UNITS))
    # base unit price: log-normal spread from ~20 to ~50,000 INR
    prod_base_price.append(round(float(np.exp(rng.normal(6.5, 1.6))), 2))

products = pd.DataFrame({
    "product_id": product_ids,
    "product_name": prod_names,
    "category": prod_cats,
    "unit_of_measure": prod_units,
    "standard_unit_price": prod_base_price,
})

# ----------------------------------------------------------------------
# 3. PURCHASES  (with fraud injection)
# ----------------------------------------------------------------------
vendor_arr = vendors["vendor_id"].to_numpy()
product_arr = products[["product_id", "standard_unit_price"]].to_numpy()
product_price_map = dict(zip(products["product_id"], products["standard_unit_price"]))
product_ids_arr = products["product_id"].to_numpy()

# Give every (vendor, product) pair a stable "historical average price" that is
# the product's standard price nudged by a vendor-specific multiplier (some vendors
# are just pricier / cheaper than others for the same goods — realistic variation).
vendor_price_multiplier = {v: float(np.clip(rng.normal(1.0, 0.12), 0.75, 1.3)) for v in vendor_arr}

n = N_PURCHASES
purchase_ids = [f"PO{1000000+i}" for i in range(n)]
sel_vendor = rng.choice(vendor_arr, size=n)
sel_product = rng.choice(product_ids_arr, size=n)
purchase_dates = [random_date(DATE_START, DATE_END) for _ in range(n)]
quantities = rng.integers(1, 500, size=n)
requesters = rng.choice(EMPLOYEES, size=n)

base_unit_prices = np.array([
    product_price_map[p] * vendor_price_multiplier[v]
    for p, v in zip(sel_product, sel_vendor)
])
# natural noise around the historical average (legitimate price variance)
noisy_unit_prices = base_unit_prices * np.clip(rng.normal(1.0, 0.06, size=n), 0.8, 1.25)
noisy_unit_prices = np.round(noisy_unit_prices, 2)

purchase_amount = np.round(noisy_unit_prices * quantities, 2)

# --- decide which rows are fraud, and by which mechanism(s) ---
is_fraud = rng.random(n) < FRAUD_RATE
# among fraud rows, assign 1-2 mechanisms (some rows combine patterns)
mech_choices = ["price_inflation", "invoice_mismatch", "round_number_invoice", "rushed_payment"]
fraud_mechanisms = [[] for _ in range(n)]
fraud_idx = np.where(is_fraud)[0]
for i in fraud_idx:
    k = 1 if rng.random() < 0.7 else 2   # 70% single pattern, 30% combined
    chosen = rng.choice(mech_choices, size=k, replace=False)
    fraud_mechanisms[i] = list(chosen)

# Apply price inflation directly to purchases (invoice/payment mechanisms applied later)
final_unit_price = noisy_unit_prices.copy()
final_amount = purchase_amount.copy()
for i in fraud_idx:
    if "price_inflation" in fraud_mechanisms[i]:
        inflate_factor = rng.uniform(1.4, 2.8)
        final_unit_price[i] = round(final_unit_price[i] * inflate_factor, 2)
        final_amount[i] = round(final_unit_price[i] * quantities[i], 2)

# NOTE: to avoid trivial separability, we also inflate a small share of NON-fraud
# purchases (legitimate premium/rush orders) so price alone isn't a perfect signal.
legit_premium_idx = rng.choice(np.where(~is_fraud)[0], size=int(0.015 * n), replace=False)
for i in legit_premium_idx:
    bump = rng.uniform(1.15, 1.5)
    final_unit_price[i] = round(final_unit_price[i] * bump, 2)
    final_amount[i] = round(final_unit_price[i] * quantities[i], 2)

fraud_label = is_fraud.astype(int)
fraud_reason = [";".join(m) for m in fraud_mechanisms]

purchases = pd.DataFrame({
    "purchase_id": purchase_ids,
    "vendor_id": sel_vendor,
    "product_id": sel_product,
    "requested_by": requesters,
    "purchase_date": purchase_dates,
    "quantity": quantities,
    "unit_price": final_unit_price,
    "purchase_amount": final_amount,
    "fraud_label": fraud_label,
    "fraud_reason": fraud_reason,
})

# ----------------------------------------------------------------------
# 4. INVOICES
# ----------------------------------------------------------------------
invoice_ids = [f"INV{2000000+i}" for i in range(n)]
invoice_dates = [pd + timedelta(days=int(rng.integers(0, 10))) for pd in purchase_dates]
invoice_numbers = [f"IN-{rng.integers(100000, 999999)}" for _ in range(n)]

invoice_amount = final_amount.copy()

for i in fraud_idx:
    mechs = fraud_mechanisms[i]
    if "invoice_mismatch" in mechs:
        # invoice differs from the actual purchase amount by 8-40%, over or under
        direction = rng.choice([-1, 1])
        pct = rng.uniform(0.08, 0.40)
        invoice_amount[i] = round(invoice_amount[i] * (1 + direction * pct), 2)
    if "round_number_invoice" in mechs:
        # force a suspiciously round figure near the true amount
        magnitude = 1000 if invoice_amount[i] < 20000 else 5000
        invoice_amount[i] = float(round(invoice_amount[i] / magnitude) * magnitude)
        if invoice_amount[i] == 0:
            invoice_amount[i] = float(magnitude)

# small amount of natural rounding noise in legitimate invoices too (rounding to nearest rupee etc.)
non_fraud_idx = np.where(~is_fraud)[0]
minor_noise_idx = rng.choice(non_fraud_idx, size=int(0.03 * len(non_fraud_idx)), replace=False)
for i in minor_noise_idx:
    invoice_amount[i] = round(invoice_amount[i] * np.clip(rng.normal(1.0, 0.01), 0.97, 1.03), 2)

invoices = pd.DataFrame({
    "invoice_id": invoice_ids,
    "purchase_id": purchase_ids,
    "vendor_id": sel_vendor,
    "invoice_date": invoice_dates,
    "invoice_number": invoice_numbers,
    "invoice_amount": np.round(invoice_amount, 2),
})

# ----------------------------------------------------------------------
# 5. PAYMENTS
# ----------------------------------------------------------------------
payment_ids = [f"PAY{3000000+i}" for i in range(n)]
payment_methods = rng.choice(["Bank Transfer", "Cheque", "NEFT", "RTGS", "UPI"], size=n,
                              p=[0.45, 0.1, 0.25, 0.15, 0.05])
approvers = rng.choice(EMPLOYEES, size=n)

# normal approval cycle: 5-30 days after invoice date
days_to_pay = rng.integers(5, 31, size=n).astype(float)

for i in fraud_idx:
    if "rushed_payment" in fraud_mechanisms[i]:
        days_to_pay[i] = rng.integers(0, 2)   # same-day / next-day approval

# tiny share of legitimate rush payments (e.g. urgent supplier needs), to avoid
# days_to_pay being a perfect proxy for fraud
legit_rush_idx = rng.choice(non_fraud_idx, size=int(0.01 * len(non_fraud_idx)), replace=False)
for i in legit_rush_idx:
    days_to_pay[i] = rng.integers(0, 3)

payment_dates = [inv_d + timedelta(days=int(d)) for inv_d, d in zip(invoice_dates, days_to_pay)]
payment_amount = invoice_amount.copy()  # payments settle the invoiced amount

payments = pd.DataFrame({
    "payment_id": payment_ids,
    "invoice_id": invoice_ids,
    "vendor_id": sel_vendor,
    "payment_date": payment_dates,
    "payment_amount": np.round(payment_amount, 2),
    "payment_method": payment_methods,
    "approved_by": approvers,
    "days_to_pay": days_to_pay.astype(int),
})

# ----------------------------------------------------------------------
# WRITE OUTPUT
# ----------------------------------------------------------------------
vendors.to_csv(os.path.join(OUT_DIR, "vendors.csv"), index=False)
products.to_csv(os.path.join(OUT_DIR, "products.csv"), index=False)
purchases.to_csv(os.path.join(OUT_DIR, "purchases.csv"), index=False)
invoices.to_csv(os.path.join(OUT_DIR, "invoices.csv"), index=False)
payments.to_csv(os.path.join(OUT_DIR, "payments.csv"), index=False)

print("Generation complete.")
print(f"vendors:   {len(vendors):,} rows  | shell-cluster vendors: {vendors['shell_cluster_id'].notna().sum():,}")
print(f"products:  {len(products):,} rows")
print(f"purchases: {len(purchases):,} rows | fraud rate: {purchases['fraud_label'].mean():.2%}")
print(f"invoices:  {len(invoices):,} rows")
print(f"payments:  {len(payments):,} rows")
print(purchases['fraud_reason'].value_counts().head(10))

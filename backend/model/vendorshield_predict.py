"""
VendorShield - Part 3 Deliverable (Person 3), unmodified scoring logic.

Adapted by Person 4 ONLY to resolve _MODEL_PATH / _METRICS_PATH relative to
this file's own directory (so the API works regardless of the process's
working directory). No scoring, thresholding, or SHAP logic was changed.

See vendorshield_model_spec.json for the authoritative field-by-field
input/output contract.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import shap

_HERE = Path(__file__).resolve().parent
_MODEL_PATH = _HERE / "vendorshield_model_v1.joblib"
_METRICS_PATH = _HERE / "metrics_summary.json"

_pipe = joblib.load(_MODEL_PATH)
_preprocessor = _pipe.named_steps["prep"]
_clf = _pipe.named_steps["clf"]
_explainer = shap.TreeExplainer(_clf)

with open(_METRICS_PATH) as f:
    _metrics = json.load(f)

RISK_HIGH = _metrics["risk_bands"]["high"]
RISK_MEDIUM = _metrics["risk_bands"]["medium"]
FEATURE_COLUMNS = _metrics["feature_columns"]

FEATURE_LABELS = {
    "price_deviation_ratio": "unit price is {val:.1f}x the vendor's historical average",
    "is_round_invoice": "invoice amount is a suspiciously round number",
    "invoice_amount_round_1000": "invoice amount lands exactly on a ₹1,000 boundary",
    "invoice_amount_round_5000": "invoice amount lands exactly on a ₹5,000 boundary",
    "is_rushed_payment": "payment was approved same-day/next-day after invoicing",
    "days_invoice_to_payment": "only {val:.0f} days between invoice and payment",
    "days_to_pay": "payment settled within {val:.0f} days of invoicing (unusually fast)",
    "invoice_purchase_pct_diff": "invoice amount differs from purchase amount by {val:.1f}%",
    "is_suspected_shell_vendor": "vendor shares banking/tax details with another vendor (possible shell entity)",
    "purchase_before_vendor_registration": "purchase occurred before the vendor was registered",
    "vendor_tenure_days_at_purchase": "vendor had only {val:.0f} days of tenure at time of purchase",
    "unit_price": "unit price of ₹{val:,.2f} is unusually high",
    "purchase_amount": "purchase amount of ₹{val:,.2f} is unusually high",
    "days_purchase_to_payment": "only {val:.0f} days from purchase to payment",
    "days_purchase_to_invoice": "only {val:.0f} days from purchase to invoicing",
    "vendor_historical_avg_price": "vendor's historical average price is ₹{val:,.2f}",
    "invoice_amount": "invoice amount of ₹{val:,.2f}",
    "payment_amount": "payment amount of ₹{val:,.2f}",
    "standard_unit_price": "standard catalog price is ₹{val:,.2f}",
    "quantity": "quantity of {val:.0f} units",
}


def _raw_feature_name(transformed_name: str) -> str:
    for prefix in ("cat__", "num__", "bool__"):
        if transformed_name.startswith(prefix):
            return transformed_name[len(prefix):]
    return transformed_name


def _plain_language_reason(raw_col, raw_value):
    if raw_col in FEATURE_LABELS:
        template = FEATURE_LABELS[raw_col]
        if isinstance(raw_value, (int, float, np.integer, np.floating)):
            return template.format(val=raw_value)
        return template
    for cat_col in ["vendor_category", "region", "category_product",
                     "unit_of_measure", "payment_method"]:
        if raw_col.startswith(cat_col + "_"):
            val = raw_col[len(cat_col) + 1:]
            return f"{cat_col.replace('_', ' ')} is '{val}' (unusual pattern for this category)"
    return f"{raw_col.replace('_', ' ')} = {raw_value}"


def _risk_level(prob: float) -> str:
    if prob >= RISK_HIGH:
        return "High"
    elif prob >= RISK_MEDIUM:
        return "Medium"
    return "Low"


def predict_fraud(transaction: dict, top_k: int = 3) -> dict:
    """
    Score a single transaction and return fraud probability, risk level,
    and plain-language top reasons.

    Parameters
    ----------
    transaction : dict
        Must contain all keys listed in FEATURE_COLUMNS (see
        vendorshield_model_spec.json). Extra keys are ignored.
    top_k : int
        Number of top contributing reasons to return (default 3).

    Returns
    -------
    dict with keys: fraud_probability (float), risk_level (str),
    top_reasons (list[str])
    """
    row = pd.DataFrame([{col: transaction[col] for col in FEATURE_COLUMNS}])
    proba = float(_pipe.predict_proba(row)[:, 1][0])

    x_transformed = _preprocessor.transform(row)
    shap_values = _explainer.shap_values(x_transformed)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]
    sv = np.asarray(shap_values).reshape(-1)
    feature_names = _preprocessor.get_feature_names_out()

    order = np.argsort(sv)[::-1]
    reasons, seen = [], set()
    for idx in order:
        if sv[idx] <= 0 or len(reasons) >= top_k:
            break
        t_name = feature_names[idx]
        raw_col = _raw_feature_name(t_name)
        if raw_col in seen:
            continue
        seen.add(raw_col)
        raw_value = row[raw_col].values[0] if raw_col in row.columns else None
        reasons.append(_plain_language_reason(raw_col, raw_value))

    return {
        "fraud_probability": round(proba, 4),
        "risk_level": _risk_level(proba),
        "top_reasons": reasons,
    }

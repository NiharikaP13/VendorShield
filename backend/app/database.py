"""SQLite-backed data access for the held-out historical audit portfolio."""
from __future__ import annotations

import os
import sqlite3
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from functools import lru_cache

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("VENDORSHIELD_DB_PATH", ROOT / "data" / "vendorshield.db"))

FILTERABLE = {
    "vendor_id": "vendor_id",
    "risk_level": "risk_level",
    "category": "category_product",
    "region": "region",
    "payment_method": "payment_method",
    "review_status": "review_status",
}


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise RuntimeError(
            f"VendorShield database not found at {DB_PATH}. "
            "Run: python scripts/build_database.py"
        )
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA cache_size = -64000")
    conn.execute("PRAGMA mmap_size = 268435456")
    return conn


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value if v not in (None, "")]


def build_where(filters: dict[str, Any]) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    for key, column in FILTERABLE.items():
        values = _as_list(filters.get(key))
        if values:
            placeholders = ",".join("?" for _ in values)
            clauses.append(f"{column} IN ({placeholders})")
            params.extend(values)

    if filters.get("date_from"):
        clauses.append("purchase_date >= ?")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        clauses.append("purchase_date <= ?")
        params.append(filters["date_to"])
    if filters.get("min_probability") is not None:
        clauses.append("fraud_probability >= ?")
        params.append(float(filters["min_probability"]))
    if filters.get("shell_only"):
        clauses.append("is_suspected_shell_vendor = 1")
    if filters.get("search"):
        term = f"%{str(filters['search']).strip()}%"
        clauses.append(
            "(purchase_id LIKE ? OR vendor_id LIKE ? OR vendor_name LIKE ? "
            "OR invoice_number LIKE ? OR purchase_order_number LIKE ? OR product_name LIKE ? OR category_product LIKE ? OR region LIKE ? OR purchase_id IN (SELECT purchase_id FROM cases WHERE case_id LIKE ?))"
        )
        params.extend([term] * 9)

    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


@lru_cache(maxsize=1)
def health() -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()
        return {"database_path": str(DB_PATH), "transaction_count": row["n"]}


@lru_cache(maxsize=1)
def options() -> dict[str, Any]:
    with connect() as conn:
        vendors = [dict(r) for r in conn.execute(
            "SELECT vendor_id, vendor_name FROM transactions "
            "GROUP BY vendor_id, vendor_name ORDER BY vendor_name"
        )]
        categories = [r[0] for r in conn.execute(
            "SELECT DISTINCT category_product FROM transactions ORDER BY category_product"
        )]
        vendor_categories = [r[0] for r in conn.execute(
            "SELECT DISTINCT vendor_category FROM transactions ORDER BY vendor_category"
        )]
        units = [r[0] for r in conn.execute(
            "SELECT DISTINCT unit_of_measure FROM transactions ORDER BY unit_of_measure"
        )]
        regions = [r[0] for r in conn.execute(
            "SELECT DISTINCT region FROM transactions ORDER BY region"
        )]
        methods = [r[0] for r in conn.execute(
            "SELECT DISTINCT payment_method FROM transactions ORDER BY payment_method"
        )]
        dates = conn.execute(
            "SELECT MIN(purchase_date) AS min_date, MAX(purchase_date) AS max_date FROM transactions"
        ).fetchone()
        return {
            "vendors": vendors,
            "categories": categories,
            "vendor_categories": vendor_categories,
            "units_of_measure": units,
            "regions": regions,
            "payment_methods": methods,
            "risk_levels": ["High", "Medium", "Low"],
            "review_statuses": ["Pending", "Assigned", "In Review", "Escalated", "Cleared After Review", "Confirmed Issue", "Insufficient Evidence"],
            "min_date": dates["min_date"],
            "max_date": dates["max_date"],
        }


def _summary_uncached(filters: dict[str, Any]) -> dict[str, Any]:
    where, params = build_where(filters)
    with connect() as conn:
        totals = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total_transactions,
                SUM(CASE WHEN risk_level='High' THEN 1 ELSE 0 END) AS high_risk_count,
                SUM(CASE WHEN risk_level='Medium' THEN 1 ELSE 0 END) AS medium_risk_count,
                SUM(CASE WHEN risk_level='Low' THEN 1 ELSE 0 END) AS low_risk_count,
                COALESCE(SUM(invoice_amount), 0) AS total_invoice_amount,
                COALESCE(SUM(CASE WHEN risk_level='High' THEN invoice_amount ELSE 0 END), 0) AS amount_at_risk,
                COALESCE(AVG(fraud_probability), 0) AS avg_probability,
                COALESCE(AVG(fraud_label), 0) AS observed_fraud_rate,
                SUM(CASE WHEN review_status IN ('In Review','Escalated') THEN 1 ELSE 0 END) AS active_reviews
            FROM transactions {where}
            """,
            params,
        ).fetchone()
        total = totals["total_transactions"] or 0

        risk_rows = conn.execute(
            f"SELECT risk_level, COUNT(*) AS count FROM transactions {where} "
            "GROUP BY risk_level ORDER BY CASE risk_level WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END",
            params,
        ).fetchall()

        trend_rows = conn.execute(
            f"""
            SELECT substr(purchase_date,1,7) AS period,
                   COUNT(*) AS total,
                   SUM(CASE WHEN risk_level='High' THEN 1 ELSE 0 END) AS High,
                   SUM(CASE WHEN risk_level='Medium' THEN 1 ELSE 0 END) AS Medium,
                   SUM(CASE WHEN risk_level='Low' THEN 1 ELSE 0 END) AS Low,
                   AVG(fraud_probability) AS avg_probability
            FROM transactions {where}
            GROUP BY substr(purchase_date,1,7)
            ORDER BY period
            """,
            params,
        ).fetchall()

        vendor_rows = conn.execute(
            f"""
            SELECT vendor_id, vendor_name,
                   COUNT(*) AS transaction_count,
                   SUM(CASE WHEN risk_level='High' THEN 1 ELSE 0 END) AS high_risk_count,
                   AVG(fraud_probability) AS avg_probability,
                   SUM(invoice_amount) AS invoice_amount,
                   MAX(is_suspected_shell_vendor) AS shell_vendor_signal
            FROM transactions {where}
            GROUP BY vendor_id, vendor_name
            HAVING COUNT(*) > 0
            ORDER BY high_risk_count DESC, avg_probability DESC
            LIMIT 20
            """,
            params,
        ).fetchall()

        category_rows = conn.execute(
            f"""
            SELECT category_product AS category,
                   COUNT(*) AS transaction_count,
                   SUM(CASE WHEN risk_level='High' THEN 1 ELSE 0 END) AS high_risk_count,
                   AVG(fraud_probability) AS avg_probability,
                   SUM(invoice_amount) AS invoice_amount
            FROM transactions {where}
            GROUP BY category_product
            ORDER BY avg_probability DESC
            """,
            params,
        ).fetchall()

        status_rows = conn.execute(
            f"SELECT review_status, COUNT(*) AS count FROM transactions {where} GROUP BY review_status",
            params,
        ).fetchall()

        return {
            "total_transactions": total,
            "high_risk_count": totals["high_risk_count"] or 0,
            "medium_risk_count": totals["medium_risk_count"] or 0,
            "low_risk_count": totals["low_risk_count"] or 0,
            "total_invoice_amount": round(float(totals["total_invoice_amount"] or 0), 2),
            "amount_at_risk": round(float(totals["amount_at_risk"] or 0), 2),
            "flagged_rate": round((totals["high_risk_count"] or 0) / total, 6) if total else 0,
            "avg_probability": round(float(totals["avg_probability"] or 0), 6),
            "observed_fraud_rate": round(float(totals["observed_fraud_rate"] or 0), 6),
            "active_reviews": totals["active_reviews"] or 0,
            "risk_distribution": [dict(r) for r in risk_rows],
            "fraud_trend": [dict(r) for r in trend_rows],
            "vendor_rollups": [dict(r) for r in vendor_rows],
            "category_rollups": [dict(r) for r in category_rows],
            "review_status_counts": [dict(r) for r in status_rows],
        }


def _filters_are_empty(filters: dict[str, Any]) -> bool:
    return not any(value not in (None, False, "", [], ()) for value in filters.values())


@lru_cache(maxsize=1)
def default_summary() -> dict[str, Any]:
    return _summary_uncached({})


def summary(filters: dict[str, Any]) -> dict[str, Any]:
    if _filters_are_empty(filters):
        # Return a shallow copy so response serialization cannot mutate the cache.
        return dict(default_summary())
    return _summary_uncached(filters)


def warm_cache() -> None:
    """Precompute common dashboard reads without blocking API startup."""
    try:
        health()
        options()
        default_summary()
    except Exception:
        pass


SORT_COLUMNS = {
    "purchase_date": "purchase_date",
    "fraud_probability": "fraud_probability",
    "invoice_amount": "invoice_amount",
    "vendor_name": "vendor_name",
    "risk_level": "CASE risk_level WHEN 'High' THEN 3 WHEN 'Medium' THEN 2 ELSE 1 END",
    "review_status": "review_status",
}


def list_transactions(
    filters: dict[str, Any],
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "fraud_probability",
    sort_order: str = "desc",
) -> dict[str, Any]:
    page = max(1, int(page))
    page_size = max(10, min(200, int(page_size)))
    sort_expr = SORT_COLUMNS.get(sort_by, SORT_COLUMNS["fraud_probability"])
    direction = "ASC" if str(sort_order).lower() == "asc" else "DESC"
    where, params = build_where(filters)
    offset = (page - 1) * page_size

    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM transactions {where}", params).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT purchase_id, purchase_date, vendor_id, vendor_name, region,
                   product_name, category_product, invoice_number, purchase_order_number, invoice_amount,
                   payment_method, fraud_probability, risk_level,
                   is_suspected_shell_vendor, purchase_before_vendor_registration,
                   review_status, reviewed_by, reviewed_at, source
            FROM transactions {where}
            ORDER BY {sort_expr} {direction}, purchase_id ASC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()
        return {
            "items": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if total else 0,
        }


def transaction_detail(purchase_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM transactions WHERE purchase_id = ?", [purchase_id]).fetchone()
        return dict(row) if row else None


def update_review(purchase_id: str, status: str, note: str, reviewed_by: str) -> dict[str, Any] | None:
    clean_note = note.strip()
    reset_to_pending = status == "Pending" and not clean_note
    now = "" if reset_to_pending else datetime.now(timezone.utc).isoformat()
    reviewer = "" if reset_to_pending else reviewed_by
    with connect() as conn:
        cursor = conn.execute(
            """
            UPDATE transactions
            SET review_status=?, review_note=?, reviewed_by=?, reviewed_at=?
            WHERE purchase_id=?
            """,
            [status, clean_note, reviewer, now, purchase_id],
        )
        if cursor.rowcount == 0:
            return None
        conn.commit()
    default_summary.cache_clear()
    return transaction_detail(purchase_id)



def insert_assessment(payload: dict[str, Any], prediction: dict[str, Any], reviewed_by: str) -> dict[str, Any]:
    """Persist a newly scored transaction so it appears in the review queue."""
    now = datetime.now(timezone.utc)
    purchase_date = datetime.fromisoformat(str(payload["purchase_date"])).date()
    invoice_date = purchase_date + timedelta(days=int(payload["days_purchase_to_invoice"]))
    payment_date = invoice_date + timedelta(days=int(payload["days_invoice_to_payment"]))
    tenure = int(payload["vendor_tenure_days_at_purchase"])
    if int(payload["purchase_before_vendor_registration"]):
        registration_date = purchase_date + timedelta(days=max(1, min(30, tenure or 1)))
    else:
        registration_date = purchase_date - timedelta(days=max(0, tenure))

    suffix = secrets.token_hex(4).upper()
    purchase_id = f"NEW-{now.strftime('%Y%m%d%H%M%S')}-{suffix}"
    invoice_id = f"INV-{suffix}"
    payment_id = f"PAY-{suffix}"

    record = {
        "purchase_id": purchase_id,
        "vendor_id": payload["vendor_id"],
        "vendor_name": payload["vendor_name"],
        "vendor_category": payload["vendor_category"],
        "region": payload["region"],
        "product_id": f"PROD-{suffix}",
        "product_name": payload["product_name"],
        "category_product": payload["category_product"],
        "unit_of_measure": payload["unit_of_measure"],
        "standard_unit_price": payload["standard_unit_price"],
        "requested_by": payload.get("requested_by", "Manual Assessment"),
        "purchase_date": purchase_date.isoformat(),
        "quantity": payload["quantity"],
        "unit_price": payload["unit_price"],
        "purchase_amount": payload["purchase_amount"],
        "invoice_id": invoice_id,
        "invoice_date": invoice_date.isoformat(),
        "invoice_number": payload["invoice_number"],
        "purchase_order_number": payload.get("purchase_order_number", ""),
        "invoice_amount": payload["invoice_amount"],
        "payment_id": payment_id,
        "payment_date": payment_date.isoformat(),
        "payment_amount": payload["payment_amount"],
        "payment_method": payload["payment_method"],
        "approved_by": payload.get("approved_by", "Pending Review"),
        "days_to_pay": payload["days_to_pay"],
        "registration_date": registration_date.isoformat(),
        "shell_cluster_id": None,
        "is_suspected_shell_vendor": payload["is_suspected_shell_vendor"],
        "purchase_before_vendor_registration": payload["purchase_before_vendor_registration"],
        "vendor_tenure_days_at_purchase": payload["vendor_tenure_days_at_purchase"],
        "vendor_historical_avg_price": payload["vendor_historical_avg_price"],
        "price_deviation_ratio": payload["price_deviation_ratio"],
        "days_purchase_to_invoice": payload["days_purchase_to_invoice"],
        "days_invoice_to_payment": payload["days_invoice_to_payment"],
        "days_purchase_to_payment": payload["days_purchase_to_payment"],
        "is_round_invoice": payload["is_round_invoice"],
        "invoice_amount_round_1000": payload["invoice_amount_round_1000"],
        "invoice_amount_round_5000": payload["invoice_amount_round_5000"],
        "invoice_purchase_pct_diff": payload["invoice_purchase_pct_diff"],
        "is_rushed_payment": payload["is_rushed_payment"],
        "fraud_label": None,
        "fraud_reason": "New assessment; ground truth unavailable",
        "fraud_probability": prediction["fraud_probability"],
        "risk_level": prediction["risk_level"],
        "review_status": "Pending",
        "review_note": "Created from New Transaction Assessment",
        "reviewed_by": reviewed_by,
        "reviewed_at": now.isoformat(),
        "source": payload.get("source", payload.get("requested_by", "Manual Assessment")),
    }

    columns = list(record)
    placeholders = ",".join("?" for _ in columns)
    with connect() as conn:
        conn.execute(
            f"INSERT INTO transactions ({','.join(columns)}) VALUES ({placeholders})",
            [record[column] for column in columns],
        )
        conn.commit()
    health.cache_clear()
    options.cache_clear()
    default_summary.cache_clear()
    return {**record, "top_reasons": prediction.get("top_reasons", [])}

def model_metrics() -> dict[str, Any]:
    with connect() as conn:
        totals = conn.execute(
            """
            SELECT COUNT(*) AS n,
                   SUM(CASE WHEN fraud_label=1 THEN 1 ELSE 0 END) AS actual_positive,
                   SUM(CASE WHEN risk_level='High' THEN 1 ELSE 0 END) AS predicted_positive,
                   SUM(CASE WHEN fraud_label=1 AND risk_level='High' THEN 1 ELSE 0 END) AS tp,
                   SUM(CASE WHEN fraud_label=0 AND risk_level='High' THEN 1 ELSE 0 END) AS fp,
                   SUM(CASE WHEN fraud_label=1 AND risk_level!='High' THEN 1 ELSE 0 END) AS fn,
                   SUM(CASE WHEN fraud_label=0 AND risk_level!='High' THEN 1 ELSE 0 END) AS tn
            FROM transactions
            """
        ).fetchone()
        tp, fp, fn, tn = (totals[k] or 0 for k in ("tp", "fp", "fn", "tn"))
        precision = tp / (tp + fp) if (tp + fp) else 0
        recall = tp / (tp + fn) if (tp + fn) else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
        return {
            "dataset_rows": totals["n"],
            "observed_fraud_rows": totals["actual_positive"],
            "high_risk_rows": totals["predicted_positive"],
            "threshold": 0.3098,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
            "reported_test_metrics": {
                "roc_auc": 0.998,
                "pr_auc": 0.980,
                "precision": 0.850,
                "recall": 0.987,
                "f1": 0.913,
            },
            "note": (
                "Reported metrics are from the held-out 60,000-row test set. "
                "Full-dataset values are shown separately and are for demonstration/evaluation only."
            ),
        }

# --- Auditor authentication helpers ---
def create_auditor(username:str, display_name:str, email:str, password_hash:str, department:str='', employee_id:str='')->dict[str,Any]:
    from backend.app.workflow import migrate, now
    migrate()
    with connect() as conn:
        if conn.execute('SELECT 1 FROM auditors WHERE email=? OR username=?',(email,username)).fetchone():
            raise ValueError('An account with this email or username already exists.')
        try:
            cur=conn.execute('INSERT INTO auditors(username,display_name,email,password_hash,department,employee_id,role,created_at) VALUES(?,?,?,?,?,?,?,?)',(username,display_name,email,password_hash,department,employee_id,'auditor',now()))
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError('An account with this email or employee ID already exists.') from exc
        return dict(conn.execute('SELECT id,username,display_name,email,department,employee_id,role,created_at,last_login_at,is_demo FROM auditors WHERE id=?',(cur.lastrowid,)).fetchone())

def find_auditor(identifier:str)->dict[str,Any]|None:
    from backend.app.workflow import migrate
    migrate()
    with connect() as conn:
        r=conn.execute('SELECT * FROM auditors WHERE lower(username)=lower(?) OR lower(email)=lower(?)',(identifier,identifier)).fetchone(); return dict(r) if r else None

def create_session(auditor_id:int, token:str, expires_at:str)->None:
    from backend.app.workflow import now
    with connect() as conn:
        conn.execute('INSERT INTO sessions(token,auditor_id,expires_at,created_at) VALUES(?,?,?,?)',(token,auditor_id,expires_at,now())); conn.commit()

def resolve_session(token:str)->dict[str,Any]|None:
    from backend.app.workflow import migrate, now
    migrate()
    with connect() as conn:
        r=conn.execute('''SELECT a.* FROM sessions s JOIN auditors a ON a.id=s.auditor_id WHERE s.token=? AND s.revoked_at IS NULL AND s.expires_at>?''',(token,now())).fetchone(); return dict(r) if r else None

def revoke_session(token:str)->None:
    from backend.app.workflow import now
    with connect() as conn: conn.execute('UPDATE sessions SET revoked_at=? WHERE token=?',(now(),token)); conn.commit()

def update_last_login(auditor_id:int)->None:
    from backend.app.workflow import now
    with connect() as conn: conn.execute('UPDATE auditors SET last_login_at=? WHERE id=?',(now(),auditor_id)); conn.commit()

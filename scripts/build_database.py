"""Build the searchable SQLite database from the supplied feature dataset.

Run from the project root:
    python scripts/build_database.py
"""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.model import vendorshield_predict as model  # noqa: E402

SOURCE = ROOT / "data" / "processed" / "vendorshield_data_features_v1.csv.gz"
DB_PATH = ROOT / "data" / "vendorshield.db"

BOOLEAN_COLUMNS = [
    "is_suspected_shell_vendor",
    "purchase_before_vendor_registration",
    "is_round_invoice",
    "invoice_amount_round_1000",
    "invoice_amount_round_5000",
    "is_rushed_payment",
]


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Processed feature data not found: {SOURCE}")

    started = time.time()
    print(f"Reading {SOURCE.name} ...")
    df = pd.read_csv(SOURCE, low_memory=False)
    source_rows = len(df)
    print(f"Loaded {source_rows:,} rows and {len(df.columns)} columns.")

    # Keep the dashboard portfolio separate from model training data. The supplied
    # report documents an 80/20 stratified split. A stable random_state=42
    # reconstruction reproduces the reported test confusion matrix within one row.
    all_indices = np.arange(source_rows)
    _, portfolio_indices = train_test_split(
        all_indices,
        test_size=0.20,
        stratify=df["fraud_label"],
        random_state=42,
    )
    df = df.iloc[portfolio_indices].copy().sort_values("purchase_id").reset_index(drop=True)
    print(f"Using {len(df):,} held-out historical rows for the auditor dashboard.")

    for col in BOOLEAN_COLUMNS:
        df[col] = df[col].astype(int)

    print("Scoring the held-out historical portfolio with the supplied model ...")
    model_frame = df[model.FEATURE_COLUMNS]
    probabilities = model._pipe.predict_proba(model_frame)[:, 1]
    df["fraud_probability"] = np.round(probabilities, 6)
    df["risk_level"] = np.select(
        [probabilities >= model.RISK_HIGH, probabilities >= model.RISK_MEDIUM],
        ["High", "Medium"],
        default="Low",
    )
    df["review_status"] = "Pending"
    df["review_note"] = ""
    df["reviewed_by"] = ""
    df["reviewed_at"] = ""

    if DB_PATH.exists():
        DB_PATH.unlink()

    print(f"Writing SQLite database to {DB_PATH} ...")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        df.to_sql("transactions", conn, index=False, if_exists="replace", chunksize=5000)
        conn.executescript(
            """
            CREATE UNIQUE INDEX idx_transactions_purchase_id ON transactions(purchase_id);
            CREATE INDEX idx_transactions_risk ON transactions(risk_level);
            CREATE INDEX idx_transactions_date ON transactions(purchase_date);
            CREATE INDEX idx_transactions_vendor ON transactions(vendor_id);
            CREATE INDEX idx_transactions_category ON transactions(category_product);
            CREATE INDEX idx_transactions_region ON transactions(region);
            CREATE INDEX idx_transactions_review ON transactions(review_status);
            CREATE INDEX idx_transactions_probability ON transactions(fraud_probability);

            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """
        )
        metadata = {
            "source_dataset_rows": str(source_rows),
            "dashboard_rows": str(len(df)),
            "portfolio_scope": "reconstructed held-out 20% stratified historical portfolio",
            "split_random_state": "42",
            "feature_count": str(len(model.FEATURE_COLUMNS)),
            "risk_high_threshold": str(model.RISK_HIGH),
            "risk_medium_threshold": str(model.RISK_MEDIUM),
            "source_file": SOURCE.name,
        }
        conn.executemany("INSERT INTO metadata(key, value) VALUES (?, ?)", metadata.items())
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("VACUUM")

    print(f"Done in {time.time() - started:.1f} seconds. Database size: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")
    print(df["risk_level"].value_counts().to_string())


if __name__ == "__main__":
    main()

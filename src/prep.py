"""
prep.py — Shared loaders: transactions, per-customer RFM table, and the monthly
acquisition-cohort retention matrix.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
CLEAN = ROOT / "data" / "online_retail_clean.csv"


def load() -> pd.DataFrame:
    df = pd.read_csv(CLEAN, parse_dates=["invoice_date"])
    df["invoice_month"] = df["invoice_date"].dt.to_period("M")
    return df


def customer_rfm(df: pd.DataFrame) -> pd.DataFrame:
    """Per-customer Recency / Frequency / Monetary + RFM segment."""
    snapshot = df["invoice_date"].max() + pd.Timedelta(days=1)
    rfm = df.groupby("customer_id").agg(
        recency_days=("invoice_date", lambda s: (snapshot - s.max()).days),
        frequency=("invoice", "nunique"),
        monetary=("revenue", "sum"),
        first_purchase=("invoice_date", "min"),
    ).reset_index()

    # 1..5 scores (recency reversed: recent = high score)
    rfm["r"] = pd.qcut(rfm["recency_days"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["f"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["m"] = pd.qcut(rfm["monetary"], 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["rfm_score"] = rfm["r"] + rfm["f"] + rfm["m"]

    def segment(row):
        if row["r"] >= 4 and row["f"] >= 4:
            return "Champions"
        if row["r"] >= 3 and row["f"] >= 3:
            return "Loyal"
        if row["r"] >= 4 and row["f"] <= 2:
            return "New / promising"
        if row["r"] <= 2 and row["f"] >= 3:
            return "At risk"
        if row["r"] <= 2 and row["f"] <= 2:
            return "Hibernating"
        return "Needs attention"

    rfm["segment"] = rfm.apply(segment, axis=1)
    return rfm


def cohort_retention(df: pd.DataFrame) -> pd.DataFrame:
    """Rows = acquisition month, cols = months since acquisition, values =
    % of the cohort active that month."""
    first = df.groupby("customer_id")["invoice_month"].min().rename("cohort")
    d = df.merge(first, on="customer_id")
    d["period"] = (d["invoice_month"] - d["cohort"]).apply(lambda x: x.n)
    sizes = d.groupby("cohort")["customer_id"].nunique()
    active = (d.groupby(["cohort", "period"])["customer_id"].nunique()
                .unstack(fill_value=0))
    retention = active.divide(sizes, axis=0) * 100
    retention.index = retention.index.astype(str)
    return retention

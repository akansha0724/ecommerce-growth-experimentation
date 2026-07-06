"""
app.py — Growth analytics dashboard (Streamlit).

Reads the summary tables written by src/analysis.py and presents them as an
interactive dashboard — the "live, clickable BI" layer. Run:
    streamlit run app.py
Deploy free on Streamlit Community Cloud (point it at this repo).
"""

from pathlib import Path

import pandas as pd
import streamlit as st

R = Path(__file__).parent / "reports"

st.set_page_config(page_title="E-commerce Growth Dashboard", page_icon="📈", layout="wide")
st.title("📈 E-commerce Growth Dashboard")
st.caption("Online Retail II (UK, 2009–2011) · cohort retention · RFM segments · revenue · "
           "companion to the A/B-test analysis in the repo")

if not (R / "rfm_segments.csv").exists():
    st.warning("Run `python src/analysis.py` first to generate the summary tables.")
    st.stop()

seg = pd.read_csv(R / "rfm_segments.csv", index_col=0)
monthly = pd.read_csv(R / "monthly_revenue.csv", index_col=0)
ret = pd.read_csv(R / "cohort_retention.csv", index_col=0)

# ── KPI row ──────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Revenue", f"£{seg['revenue'].sum()/1e6:.1f}M")
c1.metric("Customers", f"{seg['customers'].sum():,}")
top_seg = seg.sort_values("revenue", ascending=False).index[0]
c2.metric("Top segment", top_seg, f"{seg.loc[top_seg,'pct_revenue']:.0f}% of revenue")
c3.metric("Month-1 retention", f"{ret.iloc[:,1].mean():.0f}%")
top20 = (seg.sort_values('revenue', ascending=False)['pct_revenue'].cumsum())
c4.metric("Champions share", f"{seg.loc[top_seg,'pct_customers']:.0f}% of customers")

st.divider()

# ── segment explorer ─────────────────────────────────────────────────────────
left, right = st.columns([1, 1])
with left:
    st.subheader("Revenue by RFM segment")
    st.bar_chart(seg.sort_values("revenue")["revenue"] / 1e6, x_label="£M", horizontal=True)
    pick = st.selectbox("Inspect a segment", seg.index.tolist())
    row = seg.loc[pick]
    st.write(f"**{pick}** — {row['customers']:,.0f} customers "
             f"({row['pct_customers']:.0f}%), £{row['revenue']/1e6:.2f}M "
             f"({row['pct_revenue']:.0f}% of revenue), avg £{row['avg_value']:,.0f}/customer.")

with right:
    st.subheader("Monthly revenue")
    st.line_chart(monthly.iloc[:, 0], x_label="month", y_label="£M")

st.divider()

# ── cohort retention heatmap ─────────────────────────────────────────────────
st.subheader("Cohort retention (% of each acquisition cohort still active)")
st.dataframe(ret.iloc[:, :13].style.format("{:.0f}").background_gradient(cmap="Greens", axis=None),
             use_container_width=True)

st.caption("Insight: retention, not acquisition, is the lever — most cohorts drop to ~20% by "
           "month 1. Concentrate win-back spend on the highest-value segments (see the A/B test).")

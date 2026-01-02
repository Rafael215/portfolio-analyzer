# app.py
from __future__ import annotations

import shlex
from io import StringIO
from pathlib import Path

import pandas as pd
import streamlit as st

from src.cli import build_parser
from src.core import analyze_portfolio

@st.cache_data(ttl=900)
def cached_analyze_portfolio(
    csv_path: str,
    benchmark: str,
    period: str,
    risk_free: float,
    trading_days: int,
    sort: str,
    top,
):
    return analyze_portfolio(
        csv_path,
        benchmark=benchmark,
        period=period,
        risk_free=risk_free,
        trading_days=trading_days,
        sort=sort,
        top=top,
    )

st.set_page_config(page_title="Portfolio Analyzer", layout="wide")

st.title("📈 Portfolio Analyzer Dashboard")
st.caption("Upload a holdings CSV or point to a file path. You can also paste CLI flags.")

# --- CLI flags input (engineers love this) ---
default_flags = "--file data/holdings.csv --benchmark VOO --period 1y --risk_free 0.02 --sort allocation"
flags = st.text_input("CLI flags (optional)", value=default_flags)

# Parse flags with the SAME argparse parser as your CLI
parser = build_parser()
try:
    args = parser.parse_args(shlex.split(flags))
except SystemExit:
    st.error("Invalid flags. Try something like: --benchmark SPY --period 2y --risk_free 0.02")
    st.stop()

# --- Sidebar controls (nice UI) ---
st.sidebar.header("Controls")
benchmark = st.sidebar.text_input("Benchmark", value=args.benchmark).upper().strip()
period = st.sidebar.selectbox("Period", ["6mo", "1y", "2y", "5y"], index=["6mo", "1y", "2y", "5y"].index(args.period) if args.period in ["6mo", "1y", "2y", "5y"] else 1)
risk_free = st.sidebar.number_input("Risk-free rate (annual)", min_value=0.0, max_value=0.2, value=float(args.risk_free), step=0.005, format="%.3f")
sort = st.sidebar.selectbox("Sort by", ["allocation", "pl", "ticker"], index=["allocation", "pl", "ticker"].index(args.sort))
top = st.sidebar.number_input("Top N (0 = all)", min_value=0, max_value=50, value=0, step=1)

top_val = None if top == 0 else int(top)

# --- File input: upload OR path ---
st.subheader("Holdings Input")

uploaded = st.file_uploader("Upload holdings CSV", type=["csv"])
csv_path: Path | None = None

if uploaded is not None:
    # Use uploaded file contents
    csv_text = uploaded.getvalue().decode("utf-8")
    tmp = StringIO(csv_text)
    df_uploaded = pd.read_csv(tmp)
    # Save to a temporary file path is unnecessary; core expects a path.
    # So we write to a local temp file in the repo for now.
    temp_path = Path(".streamlit_holdings.csv")
    df_uploaded.to_csv(temp_path, index=False)
    csv_path = temp_path
    st.success("Uploaded CSV loaded.")
else:
    # Use --file path from flags
    csv_path = Path(args.file)
    st.info(f"Using CSV path from flags: `{csv_path}`")

if not csv_path.exists():
    st.error(f"CSV file not found: {csv_path}")
    st.stop()

# --- Run analysis ---
with st.spinner("Fetching market data and analyzing portfolio..."):
    df, ps, bs, ss = cached_analyze_portfolio(
        str(csv_path),
        benchmark=benchmark,
        period=period,
        risk_free=risk_free,
        trading_days=args.trading_days,
        sort=sort,
        top=top_val,
    )

# --- Top metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Value", f"${ps.total_value:,.2f}")
col2.metric("Total Cost Basis", f"${ps.total_cost:,.2f}")
col3.metric("Unrealized P/L", f"${ps.total_pl:,.2f}", f"{ps.total_pl_pct:,.2f}%")
col4.metric("Relative vs Benchmark", f"{bs.relative_performance*100:+.2f}%")

# --- Table ---
st.subheader("Portfolio Snapshot")
display_df = df[
    [
        "ticker",
        "shares",
        "avg_cost",
        "price",
        "cost_basis",
        "market_value",
        "allocation_pct",
        "unrealized_pl",
        "unrealized_pl_pct",
    ]
].copy()

st.dataframe(display_df, use_container_width=True)

# --- Charts ---
st.subheader("Charts")
c1, c2 = st.columns(2)

with c1:
    st.markdown("**Allocation (% of portfolio)**")
    alloc = df[["ticker", "allocation_pct"]].set_index("ticker")
    st.bar_chart(alloc)

with c2:
    st.markdown("**Unrealized P/L ($)**")
    pl = df[["ticker", "unrealized_pl"]].set_index("ticker")
    st.bar_chart(pl)

# --- Benchmark + Sharpe sections ---
st.subheader("Benchmark Comparison")
st.write(
    {
        "Period": bs.period,
        "Portfolio return": f"{bs.portfolio_return*100:+.2f}%",
        f"{bs.benchmark.upper()} return": f"{bs.benchmark_return*100:+.2f}%",
        "Relative performance": f"{bs.relative_performance*100:+.2f}%",
    }
)

st.subheader("Risk-Adjusted Performance (Sharpe)")
st.write(
    {
        "Risk-free rate (annual)": f"{ss.risk_free_annual*100:.2f}%",
        "Portfolio Sharpe": f"{ss.portfolio_sharpe:.2f}",
        f"{bs.benchmark.upper()} Sharpe": f"{ss.benchmark_sharpe:.2f}",
    }
)

st.caption(
    "Note: Portfolio return is a weighted average of holding returns using current allocation weights. "
    "Sharpe uses daily returns annualized with ~252 trading days."
)
# app.py
from __future__ import annotations

import shlex
from io import StringIO
from pathlib import Path

import pandas as pd
import streamlit as st

from src.cli import build_parser
from src.core import analyze_portfolio

# --- Input validation helpers ---
REQUIRED_COLS = {"ticker", "shares", "avg_cost"}

# Common column name aliases users might have in random brokerage exports
COL_ALIASES = {
    "symbol": "ticker",
    "stock": "ticker",
    "security": "ticker",
    "instrument": "ticker",
    "qty": "shares",
    "quantity": "shares",
    "units": "shares",
    "shares_held": "shares",
    "avg_price": "avg_cost",
    "average_price": "avg_cost",
    "avg_cost_basis": "avg_cost",
    "cost_basis": "avg_cost",
    "cost_per_share": "avg_cost",
    "purchase_price": "avg_cost",
}

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # lower + strip column names, then rename using aliases
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    rename_map = {c: COL_ALIASES.get(c, c) for c in df.columns}
    return df.rename(columns=rename_map)

def _validate_holdings_df(df: pd.DataFrame) -> tuple[bool, str, pd.DataFrame]:
    """
    Returns: (ok, message, cleaned_df)
    cleaned_df is normalized (column names + basic type coercion) but not enriched with prices.
    """
    if df is None or df.empty:
        return False, "Your CSV appears to be empty.", df

    df = _normalize_columns(df)

    missing = sorted(list(REQUIRED_COLS - set(df.columns)))
    if missing:
        example = (
            "Incorrect CSV format. Expected columns: ticker, shares, avg_cost.\n\n"
            "Example:\n"
            "ticker,shares,avg_cost\n"
            "AAPL,10,150.00\n"
            "MSFT,5,320.00\n\n"
            f"Missing columns: {', '.join(missing)}"
        )
        return False, example, df

    # Drop fully empty rows and trim ticker strings
    df = df.dropna(how="all").copy()
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()

    # Basic ticker sanity: keep non-empty
    df = df[df["ticker"] != ""]
    if df.empty:
        return False, "No valid tickers found after cleaning. Please check the 'ticker' column.", df

    # Coerce numeric fields
    for col in ("shares", "avg_cost"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Identify bad rows for a helpful error
    bad = df[df["shares"].isna() | df["avg_cost"].isna()]
    if not bad.empty:
        preview = bad[["ticker", "shares", "avg_cost"]].head(10)
        msg = (
            "Some rows have non-numeric values for shares and/or avg_cost.\n\n"
            "Fix these rows (shown below) and try again.\n"
        )
        return False, msg, preview

    # Shares must be > 0, avg_cost >= 0
    bad2 = df[(df["shares"] <= 0) | (df["avg_cost"] < 0)]
    if not bad2.empty:
        preview = bad2[["ticker", "shares", "avg_cost"]].head(10)
        msg = (
            "Some rows have invalid values (shares must be > 0, avg_cost must be >= 0).\n\n"
            "Fix these rows (shown below) and try again.\n"
        )
        return False, msg, preview

    return True, "", df[["ticker", "shares", "avg_cost"]].copy()

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

st.title("Portfolio Analyzer Dashboard")
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
    # Use uploaded file contents (robust decode for common export encodings)
    raw = uploaded.getvalue()
    try:
        csv_text = raw.decode("utf-8")
    except UnicodeDecodeError:
        csv_text = raw.decode("utf-8-sig", errors="replace")
    tmp = StringIO(csv_text)
    df_uploaded = pd.read_csv(tmp)

    ok, message, cleaned_or_preview = _validate_holdings_df(df_uploaded)
    if not ok:
        st.error(message)
        # If we returned a preview DataFrame, show it to guide the user
        if isinstance(cleaned_or_preview, pd.DataFrame) and not cleaned_or_preview.empty:
            st.dataframe(cleaned_or_preview, use_container_width=True)
        st.stop()

    # Write only the cleaned, expected columns to a temp file for core.py
    temp_path = Path(".streamlit_holdings.csv")
    cleaned_or_preview.to_csv(temp_path, index=False)
    csv_path = temp_path
else:
    # Use --file path from flags
    csv_path = Path(args.file)
    st.info(f"Using CSV path from flags: `{csv_path}`")

    if not csv_path.exists():
        st.error(f"CSV file not found: {csv_path}")
        st.stop()

    try:
        df_local = pd.read_csv(csv_path)
    except Exception as e:
        st.error("Could not read the CSV file provided via --file. Please upload a CSV or provide a readable path.")
        st.caption(f"Details: {type(e).__name__}: {e}")
        st.stop()

    ok, message, cleaned_or_preview = _validate_holdings_df(df_local)
    if not ok:
        st.error(message)
        if isinstance(cleaned_or_preview, pd.DataFrame) and not cleaned_or_preview.empty:
            st.dataframe(cleaned_or_preview, use_container_width=True)
        st.stop()

    # Write sanitized holdings to a temp file for core.py
    temp_path = Path(".streamlit_holdings.csv")
    cleaned_or_preview.to_csv(temp_path, index=False)
    csv_path = temp_path

# --- Run analysis ---
with st.spinner("Fetching market data and analyzing portfolio..."):
    try:
        df, ps, bs, ss = cached_analyze_portfolio(
            str(csv_path),
            benchmark=benchmark,
            period=period,
            risk_free=risk_free,
            trading_days=args.trading_days,
            sort=sort,
            top=top_val,
        )
    except Exception as e:
        st.error("Could not analyze this file. Please verify your CSV is in the expected format: ticker, shares, avg_cost.")
        st.caption(f"Details: {type(e).__name__}: {e}")
        st.stop()

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
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple
import pandas as pd
import yfinance as yf


@dataclass
class PortfolioSummary:
    total_value: float
    total_cost: float
    total_pl: float
    total_pl_pct: float

@dataclass
class BenchmarkSummary:
    period: str
    benchmark: str
    portfolio_return: float
    benchmark_return: float
    relative_performance: float

@dataclass
class SharpeSummary:
    period: str
    risk_free_annual: float
    portfolio_sharpe: float
    benchmark_sharpe: float

#helpers
def _clean_holdings_df(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower() for c in df.columns]

    required = {"ticker", "shares", "avg_cost"}
    if not required.issubset(df.columns):
        raise ValueError(f"CSV must have columns {required}")

    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["shares"] = pd.to_numeric(df["shares"], errors="raise")
    df["avg_cost"] = pd.to_numeric(df["avg_cost"], errors="raise")

    # Optional: remove empty tickers
    df = df[df["ticker"].str.len() > 0].copy()
    if df.empty:
        raise ValueError("Holdings CSV has no valid rows after cleaning.")

    return df

def fetch_latest_prices(tickers: list[str], period: str = "5d") -> Dict[str, float]:
    """
    Fetch the most recent closing price for each ticker.
    period="5d" gives us a few days of data so we can safely take the last close.
    """
    prices: Dict[str, float] = {}
    for t in tickers:
        hist = yf.Ticker(t).history(period=period)
        if hist.empty or "Close" not in hist:
            raise ValueError(f"No price data returned for ticker: {t}")
        prices[t] = float(hist["Close"].iloc[-1])
    return prices

def get_return_pct(ticker: str, period: str) -> float:
    """
    Simple total return over a period using Close prices:
    (last_close / first_close) - 1
    """
    hist = yf.Ticker(ticker).history(period=period, interval="1d")
    if hist.empty or "Close" not in hist:
        raise ValueError(f"No historical data for ticker: {ticker} (period={period})")
    closes = hist["Close"].dropna()
    if len(closes) < 2:
        raise ValueError(f"Not enough data points for ticker: {ticker} (period={period})")
    return float(closes.iloc[-1] / closes.iloc[0] - 1.0)

def get_daily_returns(ticker: str, period: str) -> pd.Series:
    hist = yf.Ticker(ticker).history(period=period, interval="1d")
    if hist.empty or "Close" not in hist:
        raise ValueError(f"No daily data for ticker: {ticker} (period={period})")
    closes = hist["Close"].dropna()
    if len(closes) < 2:
        raise ValueError(f"Not enough daily data for ticker: {ticker} (period={period})")
    return closes.pct_change()

def sharpe_from_daily_returns(
    daily_returns: pd.Series,
    annual_risk_free: float,
    trading_days: int = 252
) -> float:
    daily_returns = daily_returns.dropna()
    if len(daily_returns) < 2:
        raise ValueError("Not enough daily return data to compute Sharpe ratio.")

    # Convert annual RF to daily (simple approximation)
    rf_daily = annual_risk_free / trading_days

    excess = daily_returns - rf_daily
    mean_excess = excess.mean()
    std = excess.std()

    if std == 0:
        return float("nan")

    return float((mean_excess / std) * (trading_days ** 0.5))

def analyze_portfolio(
    csv_path: str | Path,
    *,
    benchmark: str = "VOO",
    period: str = "1y",
    risk_free: float = 0.0,
    trading_days: int = 252,
    sort: str = "allocation",        
    top: Optional[int] = None
) -> Tuple[pd.DataFrame, PortfolioSummary, BenchmarkSummary, SharpeSummary]:
    """
    Returns:
      - df_out: holdings table with computed columns
      - portfolio_summary: totals (value, cost, P/L)
      - benchmark_summary: portfolio vs benchmark return over period
      - sharpe_summary: portfolio vs benchmark Sharpe over period
    """
    csv_path = Path(csv_path)
    df = _clean_holdings_df(csv_path)

    tickers = df["ticker"].tolist()

    # --- Latest prices for snapshot table ---
    prices = fetch_latest_prices(tickers, period="5d")

    df["price"] = df["ticker"].map(prices)
    df["market_value"] = df["shares"] * df["price"]
    df["cost_basis"] = df["shares"] * df["avg_cost"]
    df["unrealized_pl"] = df["market_value"] - df["cost_basis"]
    df["unrealized_pl_pct"] = (df["unrealized_pl"] / df["cost_basis"]) * 100.0

    total_value = float(df["market_value"].sum())
    total_cost = float(df["cost_basis"].sum())
    total_pl = float(df["unrealized_pl"].sum())
    total_pl_pct = float((total_pl / total_cost) * 100.0) if total_cost != 0 else float("nan")

    df["allocation_pct"] = (df["market_value"] / total_value) * 100.0 if total_value != 0 else 0.0

    # --- Sorting / top N ---
    if sort == "allocation":
        df = df.sort_values("allocation_pct", ascending=False)
    elif sort == "pl":
        df = df.sort_values("unrealized_pl", ascending=False)
    elif sort == "ticker":
        df = df.sort_values("ticker", ascending=True)
    else:
        raise ValueError("sort must be one of: allocation, pl, ticker")

    if top is not None:
        df = df.head(top)

    # --- Benchmark returns ---
    # NOTE: portfolio return computed as weighted average of holding returns
    # using CURRENT allocation weights from the snapshot.
    # For a true backtest you’d need time-varying weights and rebalancing assumptions.
    full_df_for_weights = _clean_holdings_df(csv_path)
    full_prices = fetch_latest_prices(full_df_for_weights["ticker"].tolist(), period="5d")
    full_df_for_weights["price"] = full_df_for_weights["ticker"].map(full_prices)
    full_df_for_weights["market_value"] = full_df_for_weights["shares"] * full_df_for_weights["price"]
    full_total_value = float(full_df_for_weights["market_value"].sum())
    full_df_for_weights["allocation_w"] = (
        full_df_for_weights["market_value"] / full_total_value
        if full_total_value != 0
        else 0.0
    )

    portfolio_return = 0.0
    for _, row in full_df_for_weights.iterrows():
        t = row["ticker"]
        w = float(row["allocation_w"])
        r = get_return_pct(t, period)
        portfolio_return += w * r

    benchmark_return = get_return_pct(benchmark, period)
    relative_perf = portfolio_return - benchmark_return

    bench_summary = BenchmarkSummary(
        period=period,
        benchmark=benchmark,
        portfolio_return=float(portfolio_return),
        benchmark_return=float(benchmark_return),
        relative_performance=float(relative_perf),
    )

    # --- Sharpe (risk-adjusted) ---
    ticker_weights = dict(zip(full_df_for_weights["ticker"], full_df_for_weights["allocation_w"]))

    holding_daily = {t: get_daily_returns(t, period) for t in ticker_weights.keys()}
    ret_df = pd.DataFrame(holding_daily)

    # Weighted daily return
    portfolio_daily = pd.Series(0.0, index=ret_df.index)
    for t, w in ticker_weights.items():
        portfolio_daily = portfolio_daily + (ret_df[t] * w)

    bench_daily = get_daily_returns(benchmark, period)

    # Align dates
    common_idx = portfolio_daily.dropna().index.intersection(bench_daily.dropna().index)
    portfolio_daily = portfolio_daily.loc[common_idx]
    bench_daily = bench_daily.loc[common_idx]

    portfolio_sharpe = sharpe_from_daily_returns(portfolio_daily, risk_free, trading_days)
    benchmark_sharpe = sharpe_from_daily_returns(bench_daily, risk_free, trading_days)

    sharpe_summary = SharpeSummary(
        period=period,
        risk_free_annual=risk_free,
        portfolio_sharpe=float(portfolio_sharpe),
        benchmark_sharpe=float(benchmark_sharpe),
    )

    portfolio_summary = PortfolioSummary(
        total_value=total_value,
        total_cost=total_cost,
        total_pl=total_pl,
        total_pl_pct=total_pl_pct,
    )

    return df, portfolio_summary, bench_summary, sharpe_summary
import pandas as pd
import yfinance as yf
import argparse
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description="Portfolio Analyzer (CLI)")
    parser.add_argument(
        "--file",
        default="data/holdings.csv",
        help="Path to holdings CSV (default: data/holdings.csv)",
    )
    parser.add_argument(
        "--sort",
        choices=["allocation", "pl", "ticker"],
        default="allocation",
        help="Sort output by allocation, pl (unrealized P/L), or ticker",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        help="Show only the top N rows after sorting",
    )
    parser.add_argument(
    "--benchmark",
    default="VOO",
    help="Benchmark ticker to compare against (default: VOO)",
    )
    parser.add_argument(
        "--period",
        default="1y",
        help="Lookback period for return comparison (e.g., 6mo, 1y, 2y). Default: 1y",
    )
    parser.add_argument(
    "--risk_free",
    type=float,
    default=0.0,
    help="Annual risk-free rate as a decimal (e.g., 0.02 for 2%). Default: 0.0",
    )
    parser.add_argument(
        "--trading_days",
        type=int,
        default=252,
        help="Trading days per year for annualization (default: 252)",
    )
    return parser.parse_args()

def get_return_pct(ticker: str, period: str) -> float:
    hist = yf.Ticker(ticker).history(period=period)
    if hist.empty or "Close" not in hist:
        raise ValueError(f"No return data for ticker: {ticker}")
    closes = hist["Close"].dropna()
    if len(closes) < 2:
        raise ValueError(f"Not enough data to compute return for: {ticker}")
    start = float(closes.iloc[0])
    end = float(closes.iloc[-1])
    return (end / start - 1.0) * 100.0

def sharpe_from_daily_returns(daily_returns, annual_risk_free: float, trading_days: int) -> float:
    daily_returns = daily_returns.dropna()
    if len(daily_returns) < 2:
        raise ValueError("Not enough daily return data to compute Sharpe ratio.")

    # Convert annual risk-free to daily (simple approximation)
    rf_daily = annual_risk_free / trading_days

    excess = daily_returns - rf_daily
    mean_excess = excess.mean()
    std = excess.std()

    if std == 0:
        return float("nan")

    return (mean_excess / std) * (trading_days ** 0.5)

def get_daily_returns(ticker: str, period: str) -> pd.Series:
    hist = yf.Ticker(ticker).history(period=period, interval="1d")
    if hist.empty or "Close" not in hist:
        raise ValueError(f"No daily data for ticker: {ticker}")
    closes = hist["Close"].dropna()
    return closes.pct_change()
# load holdings
args = parse_args()
csv_path = Path(args.file)

df = pd.read_csv(csv_path)
df.columns = [c.strip().lower() for c in df.columns]

required = {"ticker", "shares", "avg_cost"}
if not required.issubset(df.columns):
    raise ValueError(f"CSV must have columns {required}")

df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
df["shares"] = pd.to_numeric(df["shares"])
df["avg_cost"] = pd.to_numeric(df["avg_cost"])

tickers = df["ticker"].tolist()

#Fetch latest close for each ticker
prices = {}
for t in tickers:
    hist = yf.Ticker(t).history(period="5d")
    if hist.empty:
        raise ValueError(f"No price data returned for ticker: {t}")
    prices[t] = float(hist["Close"].iloc[-1])

#compute values
df["price"] = df["ticker"].map(prices)
df["market_value"] = df["shares"] * df["price"]
df["cost_basis"] = df["shares"] * df["avg_cost"]
df["unrealized_pl"] = df["market_value"] - df["cost_basis"]
df["unrealized_pl_pct"] = (df["unrealized_pl"] / df["cost_basis"]) * 100
total_value = df["market_value"].sum()
df["allocation_pct"] = (df["market_value"] / total_value) * 100
df_full = df.copy()

# --- Benchmark comparison (period return) ---
period = args.period
benchmark = args.benchmark.upper().strip()

# Individual holding returns over the period
df_full["return_pct"] = df_full["ticker"].apply(lambda t: get_return_pct(t, period))

# Weighted portfolio return using current weights (allocation_pct)
portfolio_return_pct = (df_full["allocation_pct"] * df_full["return_pct"]).sum() / 100.0
benchmark_return_pct = get_return_pct(benchmark, period)
alpha_pct = portfolio_return_pct - benchmark_return_pct

# --- Sharpe ratio (risk-adjusted performance) ---
weights = (df_full["allocation_pct"] / 100.0).to_dict()  # {row_index: weight} not ideal
# Better: map ticker -> weight
ticker_weights = dict(zip(df_full["ticker"], df_full["allocation_pct"] / 100.0))

# Daily returns for each holding
holding_daily_returns = {}
for t in df_full["ticker"]:
    holding_daily_returns[t] = get_daily_returns(t, period)

# Combine into a DataFrame aligned by date
ret_df = pd.DataFrame(holding_daily_returns)

# Portfolio daily return = sum(weight_i * return_i)
portfolio_daily_returns = pd.Series(0.0, index=ret_df.index)
for t, w in ticker_weights.items():
    portfolio_daily_returns = portfolio_daily_returns + (ret_df[t] * w)

# Benchmark daily returns
benchmark_daily_returns = get_daily_returns(benchmark, period)

# Align dates for fair comparison (optional but nice)
common_idx = portfolio_daily_returns.dropna().index.intersection(benchmark_daily_returns.dropna().index)
portfolio_daily_returns = portfolio_daily_returns.loc[common_idx]
benchmark_daily_returns = benchmark_daily_returns.loc[common_idx]

portfolio_sharpe = sharpe_from_daily_returns(portfolio_daily_returns, args.risk_free, args.trading_days)
benchmark_sharpe = sharpe_from_daily_returns(benchmark_daily_returns, args.risk_free, args.trading_days)

#print simple report
print("\n=== Portfolio Snapshot ===")
print(f"Total value: ${total_value:,.2f}\n")
if args.sort == "allocation":
    df = df.sort_values("allocation_pct", ascending=False)
elif args.sort == "pl":
    df = df.sort_values("unrealized_pl", ascending=False)
elif args.sort == "ticker":
    df = df.sort_values("ticker", ascending=True)

if args.top is not None:
    df = df.head(args.top)
print(df[["ticker", "shares", "avg_cost", "price", "cost_basis",
          "market_value", "allocation_pct", "unrealized_pl", "unrealized_pl_pct"]]
      .to_string(index=False, formatters={
          "avg_cost": lambda x: f"${x:,.2f}",
          "price": lambda x: f"${x:,.2f}",
          "cost_basis": lambda x: f"${x:,.2f}",
          "market_value": lambda x: f"${x:,.2f}",
          "allocation_pct": lambda x: f"{x:,.2f}%",
          "unrealized_pl": lambda x: f"{'+' if x >= 0 else '-'}${abs(x):,.2f}",
          "unrealized_pl_pct": lambda x: f"{'+' if x >= 0 else ''}{x:,.2f}%"
      }))
total_cost = df_full["cost_basis"].sum()
total_pl = df_full["unrealized_pl"].sum()
total_pl_pct = (total_pl / total_cost) * 100 if total_cost else 0

print("\n--- P/L Summary ---")
print(f"Total cost basis: ${total_cost:,.2f}")
print(f"Total unrealized P/L: ${total_pl:,.2f} ({total_pl_pct:,.2f}%)")

print("--- Benchmark Comparison ---")
print(f"Period: {period}")
print(f"Portfolio return: {portfolio_return_pct:+.2f}%")
print(f"{benchmark} return: {benchmark_return_pct:+.2f}%")
print(f"Relative performance (Portfolio - {benchmark}): {alpha_pct:+.2f}%")

print("--- Risk-Adjusted Performance (Sharpe) ---")
print(f"Risk-free rate (annual): {args.risk_free*100:.2f}%")
print(f"Portfolio Sharpe ({period}): {portfolio_sharpe:.2f}")
print(f"{benchmark} Sharpe ({period}): {benchmark_sharpe:.2f}")
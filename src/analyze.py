# src/analyze.py

from __future__ import annotations

from src.cli import build_parser
from src.core import analyze_portfolio


def main() -> None:
    args = build_parser().parse_args()

    df, ps, bs, ss = analyze_portfolio(
        args.file,
        benchmark=args.benchmark,
        period=args.period,
        risk_free=args.risk_free,
        trading_days=args.trading_days,
        sort=args.sort,
        top=args.top,
    )

    # ---- Portfolio snapshot table ----
    print("\n=== Portfolio Snapshot ===")
    print(f"Total value: ${ps.total_value:,.2f}\n")

    print(
        df[
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
        ].to_string(
            index=False,
            formatters={
                "avg_cost": lambda x: f"${x:,.2f}",
                "price": lambda x: f"${x:,.2f}",
                "cost_basis": lambda x: f"${x:,.2f}",
                "market_value": lambda x: f"${x:,.2f}",
                "allocation_pct": lambda x: f"{x:,.2f}%",
                "unrealized_pl": lambda x: f"{'+' if x >= 0 else '-'}${abs(x):,.2f}",
                "unrealized_pl_pct": lambda x: f"{'+' if x >= 0 else ''}{x:,.2f}%",
            },
        )
    )

    # ---- P/L summary ----
    print("\n--- P/L Summary ---")
    print(f"Total cost basis: ${ps.total_cost:,.2f}")
    print(f"Total unrealized P/L: ${ps.total_pl:,.2f} ({ps.total_pl_pct:,.2f}%)")

    # ---- Benchmark comparison ----
    print("--- Benchmark Comparison ---")
    print(f"Period: {bs.period}")
    print(f"Portfolio return: {bs.portfolio_return * 100:+.2f}%")
    print(f"{bs.benchmark.upper()} return: {bs.benchmark_return * 100:+.2f}%")
    print(
        f"Relative performance (Portfolio - {bs.benchmark.upper()}): {bs.relative_performance * 100:+.2f}%"
    )

    # ---- Sharpe ----
    print("--- Risk-Adjusted Performance (Sharpe) ---")
    print(f"Risk-free rate (annual): {ss.risk_free_annual * 100:.2f}%")
    print(f"Portfolio Sharpe ({ss.period}): {ss.portfolio_sharpe:.2f}")
    print(f"{bs.benchmark.upper()} Sharpe ({ss.period}): {ss.benchmark_sharpe:.2f}")


if __name__ == "__main__":
    main()
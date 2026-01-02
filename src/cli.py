import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portfolio Analyzer (CLI + Dashboard)")

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

    # Benchmark + performance settings
    parser.add_argument(
        "--benchmark",
        default="VOO",
        help="Benchmark ticker (default: VOO). Example: SPY",
    )
    parser.add_argument(
        "--period",
        default="1y",
        help="Lookback period for returns (e.g., 6mo, 1y, 2y) (default: 1y)",
    )
    parser.add_argument(
        "--risk_free",
        type=float,
        default=0.0,
        help="Annual risk-free rate as a decimal (e.g., 0.02 for 2%) (default: 0.0)",
    )
    parser.add_argument(
        "--trading_days",
        type=int,
        default=252,
        help="Trading days per year for annualization (default: 252)",
    )

    return parser
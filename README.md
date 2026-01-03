🔗 **Live Demo:** https://portfolio-analyzer-rl.streamlit.app
# Portfolio Analyzer (CLI)

A Python-based command-line tool for analyzing investment portfolios using live market data.  
The tool computes portfolio allocation, unrealized profit/loss, benchmark performance, and risk-adjusted returns.

This project was built to explore how financial advisors and portfolio managers evaluate performance relative to the market.

---

## Features

- Ingests portfolio holdings from a CSV file
- Pulls live and historical market prices using Yahoo Finance
- Computes:
  - Market value per holding
  - Portfolio allocation percentages
  - Cost basis and unrealized profit/loss
- Compares portfolio performance against a market benchmark (e.g., S&P 500 via SPY or VOO)
- Calculates **risk-adjusted performance** using the Sharpe ratio
- Fully configurable via command-line flags

---

## Tech Stack

- Python
- pandas
- yfinance
- argparse (CLI interface)

---

## Input Format

Holdings are provided via a CSV file with the following columns:

ticker,shares,avg_cost
AAPL,5,150
MSFT,2,310
VOO,1,410

Run the analyzer from the project root:

	python src/analyze.py

Common CLI Options:

	python src/analyze.py --sort pl
	python src/analyze.py --top 3
	python src/analyze.py --benchmark SPY --period 1y
	python src/analyze.py --risk_free 0.02

Available Flags:

•	--file : Path to holdings CSV

•	--sort : Sort output by allocation, unrealized P/L, or ticker

•	--top : Show only the top N holdings

•	--benchmark : Benchmark ticker (default: VOO)

•	--period : Lookback period (e.g., 6mo, 1y, 2y)

•	--risk_free : Annual risk-free rate (default: 0.0)

Sample Output:

Portfolio return (1y): +11.77%

SPY return (1y): +17.38%

Relative performance: -5.61%

Portfolio Sharpe (1y): 0.55

SPY Sharpe (1y): 0.82

ASSUMPTIONS AND LIMITATIONS:

•	Portfolio returns are calculated as a weighted average of individual holding returns using current allocation weights

•	Sharpe ratio is computed using daily returns and annualized

•	This tool does not account for transaction timing, dividends, or taxes

These assumptions are appropriate for quick performance analysis but are not a full backtesting system.

---

## Dashboard (Streamlit) + CLI Flags + Caching

This project includes both:
1) a **CLI tool** (engineer-friendly, scriptable), and  
2) a **web dashboard** (demo-friendly, visually polished).

The dashboard also supports a **CLI flags input box**, so you can paste flags like:

	benchmark SPY --period 2y --risk_free 0.02 --sort pl --top 5

Streamlit Caching (Stability Feature)

To reduce repeated calls to Yahoo Finance (yfinance) and improve reliability (especially when deployed), the dashboard caches analysis results for 15 minutes using Streamlit caching:
	•	prevents rate-limit issues
	•	speeds up refreshes and UI changes
	•	improves stability for public users

Run Locally

1) Setup environment:
   ```bash
	python3 -m venv .venv
	source .venv/bin/activate

2) Install dependencies:
	```bash
	pip install -r requirements.txt

3) Run the CLI
Recommended way (package mode):
	```bash
	python -m src.analyze --file data/holdings.csv --benchmark SPY --period 1y --risk_free 0.02
	Examples:
	python -m src.analyze --sort pl
	python -m src.analyze --top 5
	python -m src.analyze --benchmark SPY --period 2y --risk_free 0.02

6) Run the Dashboard:
	```bash
	streamlit run app.py

---

## Motivation:

This project was created to better understand how wealth management platforms evaluate portfolio performance, benchmark comparisons, and risk-adjusted returns in real-world financial contexts.


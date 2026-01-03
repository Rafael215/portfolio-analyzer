Live Demo: https://portfolio-analyzer-rl.streamlit.app

PORTFOLIO ANALYZER

Portfolio Analyzer is a Python-based portfolio analytics project that includes both a command-line interface (CLI) and a Streamlit web dashboard. It is designed to evaluate investment portfolios using live and historical market data, providing insight into allocation, performance, and risk-adjusted returns.

The project supports both scriptable workflows for engineers and an interactive dashboard for demonstrations and exploration.

⸻

FEATURES

• Ingests portfolio holdings from a CSV file
• Pulls live and historical market prices using Yahoo Finance
• Computes market value, allocation percentage, cost basis, and unrealized profit/loss per holding
• Compares portfolio performance against a configurable benchmark such as SPY or VOO
• Calculates risk-adjusted performance using the Sharpe ratio
• Fully configurable via command-line flags
• Includes a Streamlit dashboard with input validation and caching for stability

⸻

TECH STACK

• Python
• pandas
• yfinance
• Streamlit
• argparse

⸻

CSV INPUT FORMAT (REQUIRED)

Holdings must be provided in a CSV file with the following columns:

• ticker — stock or ETF ticker symbol
• shares — number of shares held
• avg_cost — average cost per share

Example holdings file description:

A CSV where each row represents a holding, including the ticker symbol, the number of shares owned, and the average purchase price per share.

The Streamlit dashboard validates uploaded CSV files and will display a clear error message if the format is incorrect. (Should be able to truncate and remove unncesesary columns if needed) 

⸻

USING THE WEB DASHBOARD (NO LOCAL SETUP REQUIRED)

The Portfolio Analyzer is also available as a live web application. No installation or command-line usage is required.

To use the web dashboard:
	1.	Open the live site:
https://portfolio-analyzer-rl.streamlit.app/
	2.	Upload your own holdings CSV using the “Upload holdings CSV” option.
Your file must include the columns: ticker, shares, and avg_cost.
	3.	In the CLI flags input box at the top of the page, remove the –file argument.
When a CSV is uploaded, the dashboard automatically uses the uploaded file.
	4.	Customize the remaining CLI flags to control the analysis.
For example, you can change:
• the benchmark (SPY, VOO, etc.)
• the lookback period (6mo, 1y, 2y, 5y)
• the risk-free rate
• how results are sorted
• how many holdings are displayed

Example dashboard flag input (after uploading a CSV):

–benchmark SPY –period 2y –risk_free 0.02 –sort pl –top 5

⸻

CLI USAGE

The CLI allows you to analyze portfolios directly from the terminal using configurable flags. You can control sorting, benchmark selection, lookback period, risk-free rate, and how many holdings are displayed.

Available CLI options include:

• File path to the holdings CSV
• Sorting by allocation, unrealized profit/loss, or ticker
• Limiting output to the top N holdings
• Selecting a benchmark ticker
• Choosing a performance lookback period
• Specifying an annual risk-free rate

The CLI outputs portfolio returns, benchmark returns, relative performance, and Sharpe ratios.

⸻

STREAMLIT DASHBOARD

The Streamlit dashboard provides an interactive interface for portfolio analysis. Users can upload a CSV file or specify a local file path, adjust analysis parameters through sidebar controls, and view results in tables and charts.

The dashboard also includes a CLI flags input box, allowing advanced users to paste the same flags used in the command-line tool.

⸻

CACHING AND STABILITY

To reduce repeated calls to Yahoo Finance and improve reliability, the dashboard caches analysis results for approximately 15 minutes. This helps prevent rate-limit issues, speeds up UI refreshes, and improves stability for public deployments.

⸻

ASSUMPTIONS AND LIMITATIONS

• Portfolio returns are calculated as a weighted average of individual holding returns using current allocation weights
• Sharpe ratio is computed using daily returns and annualized
• The tool does not account for transaction timing, dividends, taxes, or cash flows
• This is not a full historical backtesting or rebalancing engine

These assumptions make the tool suitable for quick performance analysis rather than precise portfolio simulation.

⸻

MOTIVATION

This project was created to better understand how financial advisors and wealth management platforms evaluate portfolio allocation, benchmark-relative performance, and risk-adjusted returns in real-world financial contexts.

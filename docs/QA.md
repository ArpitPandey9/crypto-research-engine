# Q&A — Crypto Research Engine v1
This file is my "interview memory" and proof of understanding.
I write answers in my own words so I can explain the system end-to-end.

---

## Day 1 — Foundation: Environment + Ingestion + Validation (BTC)

### 1) What problem are we solving with this project?
We are building a research-grade crypto pipeline that can reliably:
- ingest market data
- validate it (quality checks)
- store it reproducibly (raw + processed)
- compute research features (returns)
- later run strategies and backtests

The goal is to make the work feel cohesive and production-like, not just notebooks.

### 2) What is a virtual environment (.venv) and why do we use it?
A virtual environment is an isolated Python setup for this project.
It prevents conflicts between libraries and versions across different projects.
It helps reproducibility: someone else can install the same dependencies and run the same code.

### 3) What is an API (in simple words)?
An API is a way to request data from a server using a structured format (usually HTTP).
In our case, CoinGecko provides price data through an API endpoint.

### 4) What is a DataFrame?
A pandas DataFrame is like an Excel table in Python:
- rows and columns
- each column has a name
We use it to store and manipulate price data.

### 5) Why do we separate raw vs processed data?
- Raw data = saved as close as possible to what we downloaded (source truth).
- Processed data = cleaned and standardized for analysis (typed dates, sorted, deduplicated).
This separation improves traceability and reproducibility.

### 6) What does “data ingestion” mean?
Data ingestion means fetching data from a source (API/CSV), converting it into a structured form (DataFrame), and saving it so it can be reused.

### 7) Why do we validate data?
Validation is a quality gate.
Without validation, bad data (duplicates, missing values, wrong dates) can silently create incorrect results.
Validation ensures “garbage in → garbage out” doesn’t happen.

### 8) What checks did we implement in validation and why?
- Required columns exist: prevents schema mismatch bugs.
- Dates parse correctly: ensures time-series operations work.
- Prices are not missing and > 0: missing/invalid prices break returns.
- No duplicates per (coin_id, date): duplicates break time-series logic and can distort returns/backtests.

### 9) Why did we face duplicate (coin_id, date) rows and how did we fix it?
CoinGecko can return multiple timestamps that fall on the same calendar day.
When we convert timestamps to YYYY-MM-DD, multiple rows can collapse into the same date.
Fix: deduplicate per (coin_id, date), keeping the last timestamp as a proxy for “daily close”.

### 10) What does the Day 1 pipeline do end-to-end?
- Fetch BTC prices from CoinGecko
- Convert timestamps to date
- Validate the dataset
- Save raw and processed outputs to CSV
This creates a reproducible dataset foundation.

---

## Day 2 — Multi-Asset Pipeline + Returns Layer (BTC + ETH)

### 1) What changed from Day 1 to Day 2?
Day 1 was BTC-only ingestion and validation.
Day 2 upgraded the system to:
- ingest BTC + ETH
- save datasets in long + wide format
- compute daily returns and cumulative returns

### 2) What is long format vs wide format?
- Long format: each row is one observation (date, coin_id, price).
  Example: 2026-03-10, bitcoin, 80000
- Wide format: each row is a date and each asset is a column.
  Example: date | bitcoin | ethereum

Long is good for storage and filtering.
Wide is good for calculations like returns, correlations, and portfolios.

### 3) Why do we create a wide dataset?
Because research math becomes easy:
- returns can be computed for all assets at once
- correlation matrices are simple
- portfolio calculations become straightforward

### 4) What is a “return” and why do we compute it?
A return is the percentage change in price from one day to the next.
Returns are what strategies trade on, not raw price.
Strategies, risk metrics, and backtests all depend on returns.

### 5) What does pct_change() do?
pct_change() computes simple returns:
(today_price / yesterday_price) - 1

### 6) Why do we dropna() after pct_change()?
The first row becomes NaN because there is no “previous day” to compare against.
dropna() removes that first invalid row.

### 7) What is cumulative return / cumulative growth of $1?
Cumulative growth of $1 shows what happens if you invest $1 at the start.
We compute daily growth factors: (1 + return)
Then multiply them across time:
(1 + returns).cumprod()
This gives a growth curve that is easy to visualize.

### 8) Why do we plot cumulative growth?
Plots are a sanity check.
They quickly reveal issues like:
- missing data
- date sorting errors
- unrealistic spikes
- a flat line (usually a bug)
Visualization helps catch errors early.

### 9) What artifacts do we produce by Day 2 (what files exist)?
Saved under data/processed:
- prices_btc_eth_long_processed.csv
- prices_btc_eth_wide_processed.csv
- returns_btc_eth_wide.csv
- cum_returns_btc_eth.csv

Saved under data/raw:
- prices_btc_eth_long_raw.csv

### 10) What does the Day 2 system do end-to-end?
- Fetch BTC and ETH daily prices
- Validate data quality
- Save raw long dataset
- Create processed long dataset (typed date, sorted)
- Create processed wide dataset (date index, coin columns)
- Compute returns
- Compute cumulative growth
- Save outputs for reproducible research

---

## My “Mini Interview” (I should be able to answer quickly)

### Explain the project in 3 lines:
1) It downloads BTC/ETH daily prices, validates them, and saves clean datasets.
2) It computes daily returns and cumulative growth curves.
3) It creates a reproducible foundation for strategies and backtests.

### What is the biggest risk if you skip validation?
You can get misleading backtest results because bad data silently corrupts research.

### Why is “depth” important (feedback I received)?
A few strong, cohesive, well-engineered outputs are more credible than many shallow overlapping repos.

---

## Day 3 — Strategy Layer (MA Crossover)

### 1) What is a moving average?
A moving average is the average of the last N prices. It smooths the price series and helps identify the trend.

### 2) What is the difference between fast SMA and slow SMA?
The fast SMA reacts more quickly to recent price changes, while the slow SMA reacts more slowly and represents the broader trend.

### 3) What is a signal?
A signal is the strategy’s instruction about whether to be in the market or stay out.

### 4) What is a position?
A position is the actual market exposure taken by the strategy.

### 5) Why do we use shift(1)?
We use shift(1) so that today’s position is based on yesterday’s signal. This avoids lookahead bias.

### 6) What is lookahead bias?
Lookahead bias happens when a backtest uses information that would not have been available at the time of the real decision.

### 7) What is strategy return?
Strategy return is the return earned by the strategy after applying the position rules to the asset return.

### 8) What is the difference between equity_asset and equity_strategy?
equity_asset shows the growth of $1 in buy-and-hold, while equity_strategy shows the growth of $1 under the strategy rules.

### 9) Why did the strategy outperform buy-and-hold here?
The strategy outperformed because it stayed out of the market during some weak periods and avoided part of the losses.

---

## Day 4 — Performance Metrics Layer

### 1) What is total return?
Total return shows the overall profit or loss from the beginning to the end of the backtest.

Formula:
final equity - 1

### 2) What is annualized return?
Annualized return shows what the strategy’s return would look like on a yearly basis.

It helps compare strategies fairly across different time periods.

### 3) What is annualized volatility?
Annualized volatility measures how much the returns move around on a yearly basis.

It is used as a measure of risk or instability.

### 4) What is Sharpe ratio?
Sharpe ratio measures how much return the strategy generates for each unit of risk.

A higher Sharpe ratio usually means better risk-adjusted performance.

### 5) What is max drawdown?
Max drawdown is the biggest fall from a previous peak during the backtest.

It shows the worst peak-to-trough loss.

### 6) What is exposure?
Exposure shows how much time the strategy was actually in the market.

In this project, it is calculated from the position column.

### 7) What is trade count?
Trade count shows how many times the strategy changed its position.

### 8) Why do we use results_ma_btc.csv for metrics instead of raw prices?
We use results_ma_btc.csv because it already contains the backtest outputs:
- asset_return
- strategy_return
- equity_asset
- equity_strategy
- position

These are the values needed to calculate strategy metrics.

### 9) What did Day 4 show in this project?
Day 4 showed that the strategy performed better than buy-and-hold in this backtest period because:
- strategy loss was much smaller
- volatility was lower
- max drawdown was lower
- Sharpe ratio was better
- exposure was about 50.79%
- trade count was 7

---

## Day 5 — Cost-Aware Backtesting

### 1) What is transaction cost?
Transaction cost is the cost paid when a trade happens. It can represent fees, spread, or slippage.

### 2) What is gross strategy return?
Gross strategy return is the strategy return before subtracting trading costs.

### 3) What is net strategy return?
Net strategy return is the strategy return after subtracting trading costs.

### 4) What is trade_flag?
trade_flag shows whether the position changed on a row.
- 1 = a trade happened
- 0 = no trade happened

### 5) Why do we need both gross and net strategy return?
We need both so we can compare ideal strategy performance before costs and realistic strategy performance after costs.

### 6) Why is net strategy return more realistic?
Net strategy return is more realistic because it includes transaction costs, while gross strategy return assumes trading is free.

### 7) What does cost_per_trade = 0.001 mean?
It means a transaction cost of 0.1% per trade.

### 8) What is the difference between equity_strategy_gross and equity_strategy_net?
equity_strategy_gross shows the growth of $1 before costs, while equity_strategy_net shows the growth of $1 after costs.

### 9) What did Day 5 show in this project?
Day 5 showed that the strategy still performed better than buy-and-hold after costs, but transaction costs reduced the final strategy result.

---

## Day 6 — Streamlit Frontend

### 1) What is Streamlit?
Streamlit is a Python framework used to turn Python code into an interactive web app.

### 2) Why did we add a Streamlit frontend?
We added a Streamlit frontend to make the project more usable, visible, and understandable for non-technical users such as recruiters and hiring managers.

### 3) What user inputs does the app currently support?
The app currently supports:
- Fast SMA Window
- Slow SMA Window
- Transaction Cost

### 4) Why do we use sliders for Fast SMA and Slow SMA?
We use sliders because SMA window values are integer parameters and sliders make them easy to adjust interactively.

### 5) Why do we use number_input for transaction cost?
We use number_input because transaction cost is a small decimal value and needs more precise control than a slider.

### 6) Why do we validate that Fast SMA must be smaller than Slow SMA?
We validate this because the fast moving average should be smaller than the slow moving average. If the user selects invalid values, the app shows a warning and stops instead of producing broken results.

### 7) What does st.warning() do?
st.warning() displays a warning message inside the Streamlit app.

### 8) What does st.stop() do?
st.stop() stops the app from running the remaining code after a warning or stopping condition is triggered.

### 9) Why do we import generate_signals() and backtest() into app.py?
We import them so the dashboard can use the real strategy logic already built in the project instead of rewriting it again inside the app.

### 10) Why do we use Path in app.py?
We use Path to build the file path to the processed data file in a clean and reliable way.

### 11) Why do we use chart_df instead of plotting the full results table?
We use chart_df so we only plot the most important equity columns and keep the chart clean and readable.

### 12) What does st.line_chart() do?
st.line_chart() displays a line chart in the Streamlit app using the selected DataFrame columns.

### 13) Why do we use st.columns(3)?
We use st.columns(3) to create three side-by-side layout sections so the dashboard looks cleaner and the metric cards are easier to compare.

### 14) What does col1.metric() do?
col1.metric() displays an important value with a label inside a metric card in the first column.

### 15) Why do we use iloc[-1] in the metric values?
We use iloc[-1] because we want the latest or final value from the equity curve, not the full history.

### 16) Why is the explanation section important?
The explanation section helps non-technical users understand what the dashboard is showing and what the chart and metrics mean.

### 17) Why do we include a backtest preview table?
We include a backtest preview table to make the dashboard more transparent and allow the user to inspect actual strategy output rows.

### 18) What did Day 6 add to the project?
Day 6 added an interactive Streamlit frontend that allows a user to explore the BTC moving-average crossover strategy through inputs, charts, metrics, and preview tables.
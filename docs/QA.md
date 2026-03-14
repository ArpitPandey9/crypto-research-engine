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
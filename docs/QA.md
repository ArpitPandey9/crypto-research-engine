# Q&A — Crypto Research Engine

This file is my interview memory and proof of understanding.

The purpose of this document is to help me explain the project clearly in interviews, professional reviews, and technical discussions.

---

## 1. What problem does this project solve?

This project studies whether large on-chain whale transfers can be converted into useful crypto market research signals.

Most beginner crypto projects only look at price. This project goes one layer deeper by combining:

- on-chain transfer activity
- local database storage
- market price normalization
- whale-flow signal generation
- backtesting
- dashboard presentation
- automated testing

The goal is to build a system that looks closer to a research desk workflow than a simple dashboard.

---

## 2. Why is whale-flow analysis useful?

Whales are large wallets or institutions whose transfers can affect market structure.

For example:

- large inflows into exchanges can sometimes suggest possible selling pressure
- large withdrawals from exchanges can sometimes suggest accumulation or custody movement
- repeated large transfers may reveal changing market behavior

This project does not claim whale flow is always predictive. It treats whale activity as a research signal that must be tested.

---

## 3. What is the full pipeline?

The pipeline is:

```text
Ethereum activity
      ↓
whale transfer detection
      ↓
SQLite storage
      ↓
price data download
      ↓
USD volume normalization
      ↓
enriched whale events
      ↓
rolling whale-flow signal
      ↓
cost-aware backtest
      ↓
Streamlit dashboard
      ↓
tests + CI validation
```

---

## 4. Why use SQLite?

SQLite is useful because it gives the project a real local data layer without needing a heavy external database server.

It helps with:

- reproducibility
- structured tables
- repeatable reads
- local research workflow
- easier testing

It also makes the project feel more like a system rather than a collection of loose CSV files.

---

## 5. What are the important database tables?

The main tables are:

```text
institutional_transfers
historical_prices
enriched_whales
```

`institutional_transfers` stores detected large transfers.

`historical_prices` stores market price data.

`enriched_whales` combines whale events with price information so raw token movement can become USD-denominated whale volume.

---

## 6. What does price normalization mean?

Raw token amounts are not directly comparable.

For example:

```text
10 ETH
1 WBTC
100,000 USDC
```

These have different meanings unless converted into USD.

Price normalization means converting token amounts into dollar value:

```text
token amount × token price = true USD volume
```

This allows the system to compare whale movement across assets.

---

## 7. What is rolling net whale flow?

Rolling net whale flow measures recent whale pressure over a selected time window.

The dashboard allows the user to change the rolling window.

A smaller window reacts faster.

A larger window smooths noise.

This is important because raw whale events can be noisy, but rolling flow helps reveal pressure over time.

---

## 8. How is the signal generated?

The signal is based on rolling net whale flow.

```text
positive rolling flow above threshold  → long signal
negative rolling flow below threshold  → short signal
otherwise                              → flat signal
```

The threshold prevents the model from reacting to tiny or meaningless movement.

---

## 9. Why does the backtest shift the signal?

The strategy uses the signal from one hour and applies the position from the next hour.

This prevents lookahead bias.

Without shifting, the backtest could accidentally use information from the same period it is trying to trade, which would make the result unrealistic.

---

## 10. What is lookahead bias?

Lookahead bias happens when a backtest uses information that would not have been available at the time of decision.

Example:

If I use a signal from 1 PM to trade the 1 PM return, I may be cheating because the full 1 PM data may only be known after that hour finishes.

To avoid this, the project applies:

```text
signal at time t
position at time t+1
```

---

## 11. Why include transaction costs?

A strategy that looks profitable before costs may fail after costs.

Transaction costs make the backtest more realistic.

The project calculates:

- gross strategy return
- net strategy return
- transaction cost
- trade flag

This helps compare ideal performance versus more realistic performance.

---

## 12. What does the Streamlit dashboard show?

The dashboard shows:

- selected asset
- latest whale event time
- latest market price time
- database last updated time
- number of target-asset event rows
- research frame rows
- total trades
- latest signal
- latest rolling net flow
- buy-and-hold equity
- strategy net equity
- alpha versus buy-and-hold
- equity curve comparison
- rolling whale net flow
- hourly whale USD volume
- latest research rows
- signal distribution

The dashboard is designed for research interpretation, not for direct trading instructions.

---

## 13. What do the tests prove?

The test suite checks:

- signal generation behavior
- invalid input handling
- correct target asset filtering
- exchange receiver pressure logic
- backtest column outputs
- shifted position logic
- integration with temporary SQLite databases
- CLI-style runner behavior
- Streamlit app rendering
- property-based backtest invariants

This proves the system is not just visually working; important logic is being tested.

---

## 14. Why was the SQLite CI bug important?

The CI bug happened because a test depended on a default database path.

That worked locally but failed in CI.

The fix was to use `pytest` temporary paths and pass `db_path` explicitly.

The lesson:

> Tests should be environment-independent.

This is real engineering maturity because the test should not depend on a local machine path.

---

## 15. Why did we add pytest.ini?

Local tests were failing because Python could not reliably find the `src` package.

`pytest.ini` tells pytest:

```text
pythonpath = .
testpaths = tests
```

This makes local test execution consistent.

Now:

```bash
python -m pytest -q
```

runs correctly.

---

## 16. Why is `.env` ignored?

`.env` can contain sensitive values such as RPC URLs or API keys.

Even if an RPC URL seems harmless, committing credentials is a bad habit.

The project uses `.gitignore` to protect:

- `.env`
- local database files
- virtual environments
- cache folders
- coverage artifacts

---

## 17. What is the current limitation of the project?

The project is still a research prototype.

Current limitations include:

- limited asset support
- local database dependency
- selected on-chain parsing logic
- no continuous historical indexer yet
- no production alerting system yet
- no exchange inflow/outflow classification yet
- not a financial advice engine

These limitations are acceptable because the goal is to build a strong research foundation first.

---

## 18. How would I explain this project in an interview?

I would say:

> I built a crypto research engine that detects whale transfers, stores them in SQLite, normalizes raw token movements into USD volume using market prices, converts that flow into rolling signals, backtests the strategy with transaction costs, and presents the output through a tested Streamlit dashboard.

Then I would add:

> The main learning was not just building charts. The real learning was building a reproducible pipeline, avoiding lookahead bias, making tests environment-independent, and improving the project from a learner script into a research-style system.

---

## 19. What makes this stronger than a normal beginner project?

It is stronger because it includes:

- real project structure
- data layer
- database layer
- strategy layer
- backtest layer
- dashboard layer
- testing layer
- CI/CD layer
- security hygiene
- documented limitations

A beginner dashboard usually only shows charts. This project shows system thinking.

---

## 20. What is the next high-value upgrade?

The next high-value upgrade is whale-price divergence.

Example:

```text
price rising + whales exiting       → possible distribution risk
price falling + whales accumulating → possible accumulation signal
price rising + whales accumulating  → possible trend confirmation
price falling + whales exiting      → possible danger regime
```

This would make the project more decision-maker friendly and more protocol-aware.

---

## 21. What is the long-term direction?

The long-term direction is to move from price-only research toward protocol-level analytics.

Future upgrades may include:

- exchange inflow/outflow labeling
- liquidation risk engine
- DeFi liquidity movement
- protocol state analysis
- smart contract event analysis
- Foundry-based protocol simulation
- risk scoring dashboard

The goal is to make the project look like a serious crypto research system.

---

## 22. Latest Project Update — Current System State

This section updates the older Q&A above with the latest project state.

The project now uses three main external data sources:

- Ethereum RPC: on-chain whale-transfer activity.
- Binance API: ETH/BTC historical price data.
- DEX Screener API: real DEX pool-depth / liquidity data.

SQLite is not an external data source. SQLite is the local research vault where processed evidence is stored.

Simple memory:

- Ethereum tells us what moved.
- Binance tells us what it was worth.
- DEX Screener tells us whether liquidity can absorb it.
- SQLite stores the evidence.

The latest project now includes DEX pool-depth ingestion, dex_pool_depths table, mechanism signal, automatic volatility-regime classifier, dashboard data audit script, outcome validation plan, outcome-validation dataset engine, benchmark-adjusted abnormal-return helpers, evidence-quality classification, failure-mode interpretation, full pytest discovery in CI, 162 tests passing, and latest recorded 90% coverage.

Mechanism signal combines whale flow + pool depth + volatility regime.

ETH audit result: dashboard numbers recomputed from SQLite + project formulas; automatic volatility is available; latest rolling whale-flow is zero, so no fake pool-impact signal is generated.

WBTC audit result: no whale events found for target_asset=WBTC; audit stopped honestly instead of generating fake strategy numbers.

Real-data rule: if real data is missing, show unavailable honestly instead of inventing a fake signal.

Professional explanation:

I built a crypto research engine that studies whether large on-chain whale transfers can become useful market-risk signals. It pulls whale-transfer data from Ethereum RPC, historical ETH/BTC prices from Binance, and real DEX liquidity data from DEX Screener. It stores processed data in SQLite, normalizes whale movement into USD flow, builds rolling whale-flow signals, adds liquidity and volatility context, backtests with transaction costs, and presents everything in a tested Streamlit dashboard.

The latest validation layer moves the project beyond a basic dashboard by comparing whale-flow classifications against +6h and +24h outcomes. It calculates actual return, BTC benchmark return, benchmark-adjusted abnormal return, horizon-level labels, overall labels, evidence quality, and failure-mode interpretation. This helps explain not only whether a signal worked or failed, but also whether the evidence was strong, mixed, weak, unavailable, short-lived, delayed, or unsupported.

Important limitation: this project does not claim guaranteed buy/sell signals, confirmed whale intent, financial advice, or production trading readiness.

---

## Outcome validation runner result

The project now includes `scripts/run_outcome_validation.py`, which loads real SQLite whale-event and historical-price data, builds a benchmark-adjusted outcome-validation table, prints a concise research summary, and can persist validated rows into the reusable `outcome_validation_records` SQLite dataset table.

Latest recorded ETH sample:

- rolling net flow: $1,899,322.81
- signal direction: positive
- +6h actual return: 0.7344%
- +6h BTC benchmark return: 0.9290%
- +6h abnormal return: -0.1946%
- +6h label: failed
- +24h actual return: -0.2621%
- +24h BTC benchmark return: -0.1644%
- +24h abnormal return: -0.0977%
- +24h label: failed
- overall label: failed
- evidence quality: strong
- failure mode: unsupported_signal

Professional explanation:

The first real ETH validation sample shows that a positive whale-flow signal was not supported after BTC benchmark-adjustment. At +6h, ETH was positive in raw return terms, but BTC performed better, so ETH underperformed after benchmark adjustment. At +24h, ETH also underperformed BTC. Because both horizons failed, the evidence quality is strong, but it is strong evidence against the signal. The correct failure mode is unsupported_signal.

This is a good research outcome because the project does not force the signal to look successful. It tests the signal honestly and records where the framework breaks.

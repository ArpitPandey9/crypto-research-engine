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

The project has now moved beyond a basic whale-flow dashboard.

The current system includes:

- real on-chain whale-transfer ingestion
- local SQLite research storage
- historical ETH/BTC price data
- USD normalization
- rolling whale-flow signal generation
- BTC benchmark-adjusted outcome validation
- persistent outcome-validation records
- public V2 results and sample CSV
- event-time market context V3
- tested Streamlit dashboard
- 193 local tests passing with 91% total coverage

## 23. What is outcome validation?

Outcome validation checks whether a whale-flow signal actually worked after the signal appeared.

The project does not only ask:

“Did ETH go up?”

It asks:

“Did ETH outperform BTC after the whale-flow signal?”

That matters because BTC often moves the whole crypto market. If ETH rises only because BTC rises, the whale-flow signal may not be truly useful.

## 24. Why use BTC benchmark adjustment?

BTC is used as the broad crypto-market benchmark.

The project calculates abnormal return:

ETH return minus BTC return.

This helps separate asset-specific signal behavior from general market movement.

Example:

If ETH rises 1.0% and BTC rises 0.8%, ETH only outperformed BTC by 0.2%.

That 0.2% is the benchmark-adjusted abnormal return.

## 25. What did the V2 validation result show?

The V2 sample contains 11 stored outcome-validation records.

10 records are testable and 1 record is data_unavailable.

The result is:

- 1 worked signal
- 7 failed signals
- 2 short-lived reversal signals
- 1 data_unavailable record
- 10.00% support rate

This means the current sample does not support a simple claim that positive ETH whale-flow reliably predicts durable BTC-adjusted outperformance.

## 26. What is Event-Time Market Context V3?

Event-Time Market Context V3 adds market conditions around each validated whale-flow event.

It asks:

“What did the market look like at the time of the signal?”

The two main context layers are:

- volatility context
- liquidity context

Volatility is like market weather.

Liquidity is like the market wall that absorbs or fails to absorb large flow.

## 27. Why is stale liquidity not used for flow-to-liquidity ratio?

The project does not use stale liquidity snapshots to calculate flow-to-liquidity ratio.

This is intentional.

A liquidity snapshot from many days before the event may not represent the real liquidity available at the event time.

Using that stale number as if it were fresh would make the project misleading.

So the project marks liquidity as stale and leaves flow_to_liquidity_ratio blank.

That is more honest than inventing a false precision number.

## 28. What did V3 show?

The V3 sample contains 11 event-time context rows.

The current context result is:

- 9 volatility_only_context rows
- 1 context_unavailable row
- 1 liquidity_unavailable_context row

This means volatility context is available for most records, but liquidity is stale or unavailable.

Therefore, the project can discuss volatility-context interpretation, but it cannot yet make strong liquidity-impact claims.

## 29. What do the V3 tests prove?

The V3 tests prove that the new context layer follows the honesty rules.

They check that:

- future liquidity snapshots are not used
- stale liquidity does not produce a flow-to-liquidity ratio
- missing data returns unavailable context
- invalid timestamps fail honestly
- invalid price/liquidity values fail honestly
- fresh liquidity can produce a valid ratio
- fragile market context is detected only when both volatility and liquidity conditions support it

The tests do not prove that whale-flow is predictive.

They prove that the research pipeline handles data and assumptions correctly.

## 30. How would I explain V3 in an interview?

I would say:

“After validating whether whale-flow signals worked against a BTC benchmark, I added an event-time context layer. This layer checks the volatility and liquidity conditions around each signal using only data available at or before the event time. If liquidity is stale, the system does not calculate a flow-to-liquidity ratio. This keeps the research honest and avoids false precision. The current V3 result shows that volatility context is available for most records, but liquidity context is not fresh enough yet to support strong impact-ratio conclusions.”

## 31. What is the next research improvement?

The next research improvement is historical liquidity backfill or a transparent liquidity proxy.

The reason is simple:

The project can already validate whale-flow outcomes and classify volatility context.

But to make stronger liquidity-impact claims, the system needs fresher event-time liquidity data.

Until then, stale liquidity is reported honestly as a limitation.

## 31. What is Context-Conditioned Outcome Analysis V4?

Context-Conditioned Outcome Analysis V4 summarizes validated whale-flow outcomes by event-time market context.

V2 answered whether the signal worked, failed, reversed, or became unavailable after BTC benchmark adjustment.

V3 attached event-time volatility and liquidity context to each validated record.

V4 groups those V3 context records by context bucket, volatility regime, and liquidity status, then calculates worked, failed, reversal, and data-unavailable counts.

## 32. What did V4 show?

The V4 sample contains 9 grouped summary rows generated from 11 V3 event-time context records.

The key pattern is that `volatility_only_context` dominates the sample. That group contains 9 records: 1 worked, 6 failed, and 2 reversed.

Extreme volatility contains 7 records: 1 worked and 6 failed.

Elevated volatility contains 2 records, and both are reversal outcomes.

Liquidity status is mostly stale, with 10 of 11 records marked as stale. Because of that, the project still avoids strong liquidity-impact claims.

## 33. What does V4 not prove?

V4 does not prove that volatility caused the failures or reversals.

The sample size is small, and liquidity data is mostly stale.

V4 provides an honest context-conditioned reliability summary, not causal proof.

The correct interpretation is that failed and reversal outcomes appear concentrated under certain volatility conditions, while liquidity-impact analysis remains limited until fresher event-time liquidity is available.

## 34. How would I explain V4 in an interview?

“After building V3 event-time context, I added a V4 context-conditioned outcome summary. It groups validated whale-flow records by context bucket, volatility regime, and liquidity status, then calculates support, failure, reversal, and data-unavailable rates. In the current sample, extreme volatility contains most failed outcomes, elevated volatility contains the reversal outcomes, and liquidity is mostly stale. I do not claim causality from this small sample. The value is that the project now separates signal validation from context-conditioned reliability analysis.”
---

## 35. What did the V4 research note conclude?

The V4 research note concluded that positive ETH whale-flow should not be treated as a standalone durable signal.

V4 adds context by grouping validated outcomes across event-time volatility and liquidity conditions. The important research discipline is that stale or future liquidity snapshots are not used to calculate flow-to-liquidity ratios.

This means the project can discuss volatility-regime context, but it cannot yet make strong liquidity-impact claims until historical liquidity backfill or a transparent liquidity proxy is added.

Professional summary:

“V4 moves the project from signal validation to context-conditioned reliability analysis. It keeps failed and reversal outcomes visible, avoids fake liquidity precision, and identifies event-time liquidity as the next major research limitation.”


# Crypto Research Engine

[![CI](https://github.com/ArpitPandey9/crypto-research-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/ArpitPandey9/crypto-research-engine/actions/workflows/ci.yml)

A research-grade crypto whale-flow analysis system that combines on-chain transfer detection, local SQLite storage, price normalization, whale-flow signal generation, vectorized backtesting, automated tests, and an interactive Streamlit dashboard.

This project is built as a flagship proof-of-work system for crypto quant research, DeFi analytics, and protocol-level market structure thinking.

---

## Why This Project Exists

Crypto markets are not driven only by price charts. Large wallets, exchange flows, token transfers, liquidity movement, and whale behavior can create early signals of market pressure.

This project studies a simple but important research question:

> Can large on-chain whale transfers, normalized into USD flow pressure, help explain or signal future asset behavior?

Instead of building another price-only dashboard, this project builds a full research pipeline:

```text
on-chain activity
      ↓
local SQLite vault
      ↓
historical price normalization
      ↓
whale-flow signal generation
      ↓
cost-aware backtesting
      ↓
Streamlit research dashboard
      ↓
tests + CI validation
```

---

## Current Status

The project currently includes:

- Ethereum whale transaction scanner
- Native ETH transfer detection
- Selected ERC-20 transfer parsing
- Local SQLite database vault
- Binance historical price downloader
- USD normalization of whale volume
- Enriched whale-event table
- Whale-flow signal generation
- Rolling net-flow strategy logic
- Cost-aware vectorized backtesting
- Streamlit dashboard
- Unit tests
- Integration tests
- Property-based tests
- Streamlit app tests
- GitHub Actions CI
- Coverage reporting

Current test status:

```text
33 tests passing
91% total coverage
GitHub Actions CI: green
```

---

## System Architecture

```text
src/data/onchain_client.py
        ↓
scans Ethereum blocks
        ↓
stores whale transfers in SQLite
        ↓
data/db/whale_data.db
        ↓
src/data/fetch_prices.py
        ↓
downloads ETH/BTC price data
        ↓
normalizes whale transfers into USD volume
        ↓
enriched_whales + historical_prices tables
        ↓
src/strategies/whale_signals.py
        ↓
creates rolling whale-flow signals
        ↓
runs cost-aware backtest
        ↓
src/strategies/run_whale_signals.py
        ↓
prints research summary
        ↓
app.py
        ↓
interactive Streamlit dashboard
```

---

## Repository Structure

```text
crypto-research-engine/
├── app.py
├── requirements.txt
├── pytest.ini
├── .coveragerc
├── .github/
│   └── workflows/
│       └── ci.yml
├── data/
│   └── db/
│       └── whale_data.db        # local only, ignored by git
├── docs/
│   └── QA.md
├── src/
│   ├── data/
│   │   ├── fetch_prices.py
│   │   └── onchain_client.py
│   └── strategies/
│       ├── run_whale_signals.py
│       └── whale_signals.py
└── tests/
    ├── test_app_streamlit.py
    ├── test_run_whale_signals_integration.py
    ├── test_run_whale_signals_unit.py
    ├── test_whale_signals.py
    └── test_whale_signals_properties.py
```

---

## Core Research Logic

### 1. Whale Transfer Detection

`src/data/onchain_client.py` connects to an Ethereum RPC endpoint and scans block transactions.

It detects large transfers and stores them in a local SQLite database for research.

The goal is not just to download data. The goal is to create a repeatable research vault that can later support stronger protocol-level analytics.

---

### 2. Local SQLite Vault

The project uses SQLite as a local research database.

Main tables:

```text
institutional_transfers
historical_prices
enriched_whales
```

The database file is intentionally ignored by Git:

```text
data/db/*.db
```

This keeps local generated research data out of the public repository.

---

### 3. Price Normalization

`src/data/fetch_prices.py` downloads market price data and normalizes token movement into USD value.

Example idea:

```text
ETH whale amount  × ETH price = true USD volume
WBTC whale amount × BTC price = true USD volume
stablecoin amount × 1.0       = true USD volume
```

This converts raw token movement into comparable dollar-denominated flow pressure.

---

### 4. Whale-Flow Signal Generation

`src/strategies/whale_signals.py` builds an hourly research frame.

It calculates:

- target asset price
- hourly whale pressure
- rolling net whale flow
- signal direction

Signal logic:

```text
rolling_net_flow > threshold   → long signal
rolling_net_flow < -threshold  → short signal
otherwise                      → flat signal
```

The current strategy supports:

```text
ETH
WBTC
```

---

### 5. Backtesting Methodology

The backtest is vectorized with pandas.

Important design choice:

```text
signal observed at hour t
position applied from hour t+1
```

This avoids lookahead bias.

The backtest calculates:

- asset return
- shifted strategy position
- trade flag
- transaction cost
- gross strategy return
- net strategy return
- buy-and-hold equity curve
- gross strategy equity curve
- net strategy equity curve

Transaction cost is charged when the position changes.

---

## Streamlit Dashboard

The dashboard is implemented in:

```text
app.py
```

It provides:

- target asset selection
- rolling window control
- minimum flow threshold control
- transaction cost control
- data freshness panel
- research summary metrics
- equity curve comparison
- rolling whale-flow chart
- hourly whale-volume chart
- latest research rows
- signal distribution table

Run it with:

```bash
streamlit run app.py
```

---

## How To Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/ArpitPandey9/crypto-research-engine.git
cd crypto-research-engine
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file:

```text
ETH_RPC_URL=your_ethereum_rpc_url_here
```

Do not commit `.env`.

---

## Data Pipeline Commands

### 1. Scan Ethereum data

```bash
python -m src.data.onchain_client
```

### 2. Download prices and normalize whale volume

```bash
python -m src.data.fetch_prices
```

### 3. Run whale-flow strategy summary

```bash
python -m src.strategies.run_whale_signals
```

### 4. Launch dashboard

```bash
streamlit run app.py
```

---

## Testing

Run the full test suite:

```bash
python -m pytest -q
```

Run tests with coverage:

```bash
coverage erase
coverage run -m pytest
coverage report -m
```

Current local result:

```text
33 passed
91% total coverage
```

---

## CI/CD

GitHub Actions runs the full test suite and coverage workflow on every push and pull request to `main`.

Workflow file:

```text
.github/workflows/ci.yml
```

CI currently validates:

- unit tests
- integration tests
- property-based tests
- Streamlit app tests
- coverage report
- coverage artifact upload

---

## Security Practices

This project follows basic security hygiene:

- `.env` is ignored
- database files are ignored
- coverage artifacts are ignored
- virtual environment is ignored
- secrets are never committed
- RPC URLs are loaded from environment variables

Important rule:

> Never commit private keys, API keys, RPC secrets, or wallet credentials.

---

## Current Limitations

This is a research prototype, not a production trading system.

Current limitations:

- scans limited Ethereum data depending on the current script configuration
- does not yet perform continuous historical block indexing
- supports selected assets only
- does not yet parse all event logs or internal DeFi contract flows
- local SQLite database is not committed to GitHub
- dashboard depends on locally generated database tables
- signals are research signals, not financial advice

---

## Roadmap

Near-term improvements:

- improve dashboard explanation layer
- make the UI more decision-maker friendly
- add whale-price divergence signals
- add risk scoring
- add alert labels such as Accumulation, Distribution, Danger, and Neutral
- improve database schema documentation
- add protocol-level analytics layer
- connect whale behavior to DeFi market structure

Future research extensions:

- exchange inflow/outflow classification
- liquidation-risk monitoring
- DeFi yield and liquidity dashboard
- multi-chain whale-flow ingestion
- smart-contract state analytics
- Foundry-based protocol simulation module

---

## Interview Explanation

A clear way to explain this project:

> This is a crypto research engine that detects large on-chain transfers, stores them in a local SQLite vault, normalizes token movement into USD volume using market prices, converts that movement into rolling whale-flow signals, backtests those signals with transaction costs, and presents the results through a tested Streamlit dashboard.

In simple terms:

> It studies whether whale behavior can become a useful research signal for crypto market movement.

---

## Disclaimer

This project is for research and education only. It is not financial advice, not a trading recommendation system, and not a production investment product.
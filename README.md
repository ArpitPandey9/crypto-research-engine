# Crypto Research Engine v1

A research-grade crypto data + backtesting pipeline (BTC/ETH initially). Built with reproducible datasets, clear methodology, and research-friendly structure.

## Milestones
- [x] Day 1: BTC ingestion + validation + raw/processed outputs + date range checks
- [x] Day 2: BTC+ETH ingestion + validation + long/wide datasets + returns + cumulative returns
- [x] Day 3: BTC moving-average crossover strategy + signals + backtest + equity curves
- [x] Day 4: strategy performance metrics (return, volatility, Sharpe, drawdown, exposure, trade count)

## Quickstart
```bash
python -m src.data.make_dataset
python -m src.features.returns
python -m src.strategies.run_ma_crossover
python -m src.analytics.run_metrics
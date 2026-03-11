# Crypto Research Engine v1

A research-grade crypto data + backtesting pipeline (BTC/ETH initially). Built with reproducible datasets, clear methodology, and research-friendly structure.

## Milestones
- [x] Day 1: BTC ingestion + validation + raw/processed outputs + date range checks
- [x] Day 2: BTC+ETH ingestion + validation + long/wide datasets + returns + cumulative returns

## Quickstart
```bash
python -m src.data.make_dataset
python -m src.features.returns
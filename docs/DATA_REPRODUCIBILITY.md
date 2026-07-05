# Data Reproducibility

This project intentionally does not commit the local SQLite research database:

```text
data/db/whale_data.db
```

The database is a generated local artifact. It may contain time-dependent API outputs, local research runs, and data that should be rebuilt or validated rather than treated as static source code.

## What is included in Git

The repository includes:

- source code for ingestion, enrichment, validation, and dashboard logic
- tests for the analytical and data-processing layers
- sample CSV artifacts under `data/samples/`
- documentation explaining current validation results and limitations

Current sample artifacts include:

```text
data/samples/outcome_validation_v2_sample.csv
data/samples/event_time_context_v3_sample.csv
data/samples/context_conditioned_outcomes_v4_sample.csv
```

These samples let reviewers inspect validated research-output structure without requiring the local SQLite database.

## What is not included in Git

The generated database file is not committed:

```text
data/db/whale_data.db
```

A fresh clone should be expected to run tests successfully without the database. The Streamlit dashboard and live data scripts require the database to exist locally.

## Required SQLite tables for full dashboard/runtime use

A complete local research database is expected to include:

```text
institutional_transfers
historical_prices
enriched_whales
dex_pool_depths
outcome_validation_records
```

The dashboard depends primarily on:

```text
enriched_whales
historical_prices
```

The validation and context layers may also use:

```text
dex_pool_depths
outcome_validation_records
```

## Reproducibility check

Run:

```bash
python scripts/verify_data_reproducibility.py
```

This checks whether expected sample CSV files exist, whether the local SQLite database exists, and whether required tables are present if the database exists.

By default, a missing database is treated as a warning because the database is intentionally ignored in Git.

To require the local database, run:

```bash
python scripts/verify_data_reproducibility.py --require-db
```

## Current interpretation

The repository is reproducible at the code, test, and sample-artifact level from a fresh clone.

Full dashboard/runtime reproduction requires rebuilding or restoring the local SQLite database from the data pipeline.

Until the database is present, dashboard execution should fail honestly rather than silently inventing or fabricating data.

This is intentional: missing data should be reported as unavailable, not replaced with fake or placeholder research outputs.

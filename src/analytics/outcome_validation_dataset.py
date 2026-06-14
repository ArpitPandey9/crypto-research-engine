"""Persistent dataset layer for outcome-validation research.

This module turns one-off outcome-validation tables into a reusable SQLite
research dataset.

It does not generate new signals.
It stores validated signal outcomes so the project can study reliability across
many events, regimes, labels, and failure modes.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TABLE_NAME = "outcome_validation_records"

DATASET_COLUMNS = [
    "record_key",
    "event_timestamp",
    "target_asset",
    "target_price_asset",
    "benchmark_asset",
    "signal",
    "signal_direction",
    "rolling_net_flow",
    "event_asset_price",
    "actual_return_6h",
    "benchmark_return_6h",
    "abnormal_return_6h",
    "label_6h",
    "actual_return_24h",
    "benchmark_return_24h",
    "abnormal_return_24h",
    "label_24h",
    "overall_label",
    "evidence_quality",
    "failure_mode",
    "window_hours",
    "min_flow_usd",
    "data_quality_status",
    "validation_notes",
    "created_at",
]

REQUIRED_VALIDATION_COLUMNS = {
    "event_timestamp",
    "target_asset",
    "target_price_asset",
    "benchmark_asset",
    "signal",
    "signal_direction",
    "rolling_net_flow",
    "event_asset_price",
    "6h_actual_return",
    "6h_benchmark_return",
    "6h_abnormal_return",
    "6h_label",
    "24h_actual_return",
    "24h_benchmark_return",
    "24h_abnormal_return",
    "24h_label",
    "overall_label",
    "evidence_quality",
    "failure_mode",
}

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    record_key TEXT PRIMARY KEY,
    event_timestamp TEXT NOT NULL,
    target_asset TEXT NOT NULL,
    target_price_asset TEXT,
    benchmark_asset TEXT NOT NULL,
    signal INTEGER NOT NULL,
    signal_direction TEXT NOT NULL,
    rolling_net_flow REAL,
    event_asset_price REAL,
    actual_return_6h REAL,
    benchmark_return_6h REAL,
    abnormal_return_6h REAL,
    label_6h TEXT,
    actual_return_24h REAL,
    benchmark_return_24h REAL,
    abnormal_return_24h REAL,
    label_24h TEXT,
    overall_label TEXT,
    evidence_quality TEXT,
    failure_mode TEXT,
    window_hours INTEGER NOT NULL,
    min_flow_usd REAL NOT NULL,
    data_quality_status TEXT NOT NULL,
    validation_notes TEXT,
    created_at TEXT NOT NULL
);
"""

INSERT_OR_REPLACE_SQL = f"""
INSERT OR REPLACE INTO {TABLE_NAME} (
    record_key,
    event_timestamp,
    target_asset,
    target_price_asset,
    benchmark_asset,
    signal,
    signal_direction,
    rolling_net_flow,
    event_asset_price,
    actual_return_6h,
    benchmark_return_6h,
    abnormal_return_6h,
    label_6h,
    actual_return_24h,
    benchmark_return_24h,
    abnormal_return_24h,
    label_24h,
    overall_label,
    evidence_quality,
    failure_mode,
    window_hours,
    min_flow_usd,
    data_quality_status,
    validation_notes,
    created_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""


def initialize_outcome_validation_dataset(db_path: Path) -> None:
    """Create the outcome-validation dataset table if it does not exist."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute(CREATE_TABLE_SQL)


def _to_database_value(value: Any) -> Any:
    """Convert pandas/numpy missing values into SQLite-friendly values."""
    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return str(value)

    return value


def _data_quality_status(row: pd.Series) -> str:
    """Classify whether a validation record had usable outcome data."""
    if row.get("overall_label") == "data_unavailable":
        return "data_unavailable"

    if row.get("evidence_quality") == "unavailable":
        return "data_unavailable"

    return "available"


def _record_key(row: pd.Series, window_hours: int, min_flow_usd: float) -> str:
    """Build a deterministic key so re-running the same validation is idempotent."""
    event_timestamp = str(row["event_timestamp"])
    target_asset = str(row["target_asset"]).upper()
    benchmark_asset = str(row["benchmark_asset"]).upper()
    signal = int(row["signal"])

    return (
        f"{target_asset}|{benchmark_asset}|{event_timestamp}|"
        f"window={int(window_hours)}|min_flow={float(min_flow_usd)}|signal={signal}"
    )


def prepare_outcome_validation_records(
    validation_df: pd.DataFrame,
    window_hours: int,
    min_flow_usd: float,
    validation_notes: str = "",
) -> pd.DataFrame:
    """Convert a V1 validation table into V2 dataset records."""
    if validation_df.empty:
        return pd.DataFrame(columns=DATASET_COLUMNS)

    missing = sorted(REQUIRED_VALIDATION_COLUMNS - set(validation_df.columns))
    if missing:
        raise ValueError(f"Missing required validation columns: {missing}")

    created_at = datetime.now(timezone.utc).isoformat()

    records = []

    for _, row in validation_df.iterrows():
        record = {
            "record_key": _record_key(
                row=row,
                window_hours=window_hours,
                min_flow_usd=min_flow_usd,
            ),
            "event_timestamp": str(row["event_timestamp"]),
            "target_asset": str(row["target_asset"]).upper(),
            "target_price_asset": str(row["target_price_asset"]).upper(),
            "benchmark_asset": str(row["benchmark_asset"]).upper(),
            "signal": int(row["signal"]),
            "signal_direction": str(row["signal_direction"]),
            "rolling_net_flow": _to_database_value(row["rolling_net_flow"]),
            "event_asset_price": _to_database_value(row["event_asset_price"]),
            "actual_return_6h": _to_database_value(row["6h_actual_return"]),
            "benchmark_return_6h": _to_database_value(row["6h_benchmark_return"]),
            "abnormal_return_6h": _to_database_value(row["6h_abnormal_return"]),
            "label_6h": str(row["6h_label"]),
            "actual_return_24h": _to_database_value(row["24h_actual_return"]),
            "benchmark_return_24h": _to_database_value(row["24h_benchmark_return"]),
            "abnormal_return_24h": _to_database_value(row["24h_abnormal_return"]),
            "label_24h": str(row["24h_label"]),
            "overall_label": str(row["overall_label"]),
            "evidence_quality": str(row["evidence_quality"]),
            "failure_mode": str(row["failure_mode"]),
            "window_hours": int(window_hours),
            "min_flow_usd": float(min_flow_usd),
            "data_quality_status": _data_quality_status(row),
            "validation_notes": validation_notes,
            "created_at": created_at,
        }
        records.append(record)

    records_df = pd.DataFrame(records)
    return records_df[DATASET_COLUMNS]


def save_outcome_validation_records(
    db_path: Path,
    validation_df: pd.DataFrame,
    window_hours: int,
    min_flow_usd: float,
    validation_notes: str = "",
) -> int:
    """Save validation records into SQLite and return saved row count."""
    records_df = prepare_outcome_validation_records(
        validation_df=validation_df,
        window_hours=window_hours,
        min_flow_usd=min_flow_usd,
        validation_notes=validation_notes,
    )

    if records_df.empty:
        return 0

    initialize_outcome_validation_dataset(db_path)

    rows = [
        tuple(_to_database_value(row[column]) for column in DATASET_COLUMNS)
        for _, row in records_df.iterrows()
    ]

    with sqlite3.connect(db_path) as conn:
        conn.executemany(INSERT_OR_REPLACE_SQL, rows)

    return len(records_df)


def load_outcome_validation_records(db_path: Path) -> pd.DataFrame:
    """Load all stored outcome-validation records from SQLite."""
    db_path = Path(db_path)

    if not db_path.exists():
        return pd.DataFrame(columns=DATASET_COLUMNS)

    with sqlite3.connect(db_path) as conn:
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?;",
            (TABLE_NAME,),
        ).fetchone()

        if table_exists is None:
            return pd.DataFrame(columns=DATASET_COLUMNS)

        return pd.read_sql_query(
            f"SELECT * FROM {TABLE_NAME} ORDER BY event_timestamp;",
            conn,
        )


def build_outcome_validation_dataset_summary(records_df: pd.DataFrame) -> dict[str, Any]:
    """Build research summary metrics from stored validation records."""
    if records_df.empty:
        return {
            "total_records": 0,
            "testable_records": 0,
            "supported_count": 0,
            "unsupported_count": 0,
            "reversal_count": 0,
            "delayed_reaction_count": 0,
            "inconclusive_count": 0,
            "data_unavailable_count": 0,
            "support_rate": None,
            "average_abnormal_return_6h": None,
            "average_abnormal_return_24h": None,
            "most_common_failure_mode": None,
        }

    labels = records_df["overall_label"].fillna("unknown")
    testable_mask = labels != "data_unavailable"
    testable_count = int(testable_mask.sum())
    supported_count = int((labels == "worked").sum())

    support_rate = None
    if testable_count > 0:
        support_rate = supported_count / testable_count

    failure_modes = records_df["failure_mode"].dropna()
    most_common_failure_mode = None
    if not failure_modes.empty:
        most_common_failure_mode = str(failure_modes.value_counts().idxmax())

    return {
        "total_records": int(len(records_df)),
        "testable_records": testable_count,
        "supported_count": supported_count,
        "unsupported_count": int((labels == "failed").sum()),
        "reversal_count": int((labels == "reversal").sum()),
        "delayed_reaction_count": int((labels == "delayed_reaction").sum()),
        "inconclusive_count": int((labels == "inconclusive").sum()),
        "data_unavailable_count": int((labels == "data_unavailable").sum()),
        "support_rate": support_rate,
        "average_abnormal_return_6h": pd.to_numeric(
            records_df["abnormal_return_6h"],
            errors="coerce",
        ).mean(),
        "average_abnormal_return_24h": pd.to_numeric(
            records_df["abnormal_return_24h"],
            errors="coerce",
        ).mean(),
        "most_common_failure_mode": most_common_failure_mode,
    }

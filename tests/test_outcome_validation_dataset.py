import pandas as pd
import pytest

from src.analytics.outcome_validation_dataset import (
    DATASET_COLUMNS,
    build_outcome_validation_dataset_summary,
    load_outcome_validation_records,
    prepare_outcome_validation_records,
    save_outcome_validation_records,
)


def sample_validation_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event_timestamp": "2026-04-23 09:00:00+00:00",
                "target_asset": "eth",
                "target_price_asset": "eth",
                "benchmark_asset": "btc",
                "signal": 1,
                "signal_direction": "positive",
                "rolling_net_flow": 1899322.81,
                "event_asset_price": 3000.0,
                "6h_actual_return": 0.01,
                "6h_benchmark_return": 0.004,
                "6h_abnormal_return": 0.006,
                "6h_label": "worked",
                "24h_actual_return": -0.002,
                "24h_benchmark_return": 0.003,
                "24h_abnormal_return": -0.005,
                "24h_label": "failed",
                "overall_label": "reversal",
                "evidence_quality": "mixed",
                "failure_mode": "short_lived_reaction",
            }
        ]
    )


def test_prepare_records_maps_validation_table_to_dataset_schema() -> None:
    records = prepare_outcome_validation_records(
        validation_df=sample_validation_df(),
        window_hours=12,
        min_flow_usd=0.0,
        validation_notes="unit test",
    )

    assert list(records.columns) == DATASET_COLUMNS
    assert len(records) == 1

    record = records.iloc[0]
    assert record["target_asset"] == "ETH"
    assert record["benchmark_asset"] == "BTC"
    assert record["label_6h"] == "worked"
    assert record["label_24h"] == "failed"
    assert record["overall_label"] == "reversal"
    assert record["evidence_quality"] == "mixed"
    assert record["failure_mode"] == "short_lived_reaction"
    assert record["data_quality_status"] == "available"
    assert record["validation_notes"] == "unit test"


def test_prepare_records_marks_data_unavailable_status() -> None:
    validation_df = sample_validation_df()
    validation_df.loc[0, "overall_label"] = "data_unavailable"
    validation_df.loc[0, "evidence_quality"] = "unavailable"

    records = prepare_outcome_validation_records(
        validation_df=validation_df,
        window_hours=12,
        min_flow_usd=0.0,
    )

    assert records.iloc[0]["data_quality_status"] == "data_unavailable"


def test_prepare_records_rejects_missing_required_columns() -> None:
    with pytest.raises(ValueError, match="Missing required validation columns"):
        prepare_outcome_validation_records(
            validation_df=pd.DataFrame({"event_timestamp": ["2026-01-01"]}),
            window_hours=12,
            min_flow_usd=0.0,
        )


def test_save_and_load_records_are_idempotent(tmp_path) -> None:
    db_path = tmp_path / "validation_dataset.db"

    first_count = save_outcome_validation_records(
        db_path=db_path,
        validation_df=sample_validation_df(),
        window_hours=12,
        min_flow_usd=0.0,
        validation_notes="first save",
    )

    second_count = save_outcome_validation_records(
        db_path=db_path,
        validation_df=sample_validation_df(),
        window_hours=12,
        min_flow_usd=0.0,
        validation_notes="second save",
    )

    loaded = load_outcome_validation_records(db_path)

    assert first_count == 1
    assert second_count == 1
    assert len(loaded) == 1
    assert loaded.iloc[0]["validation_notes"] == "second save"


def test_load_records_returns_empty_schema_when_table_missing(tmp_path) -> None:
    loaded = load_outcome_validation_records(tmp_path / "missing.db")

    assert loaded.empty
    assert list(loaded.columns) == DATASET_COLUMNS


def test_dataset_summary_counts_research_outcomes() -> None:
    records_df = pd.DataFrame(
        [
            {
                "overall_label": "worked",
                "failure_mode": "no_failure",
                "abnormal_return_6h": 0.01,
                "abnormal_return_24h": 0.02,
            },
            {
                "overall_label": "failed",
                "failure_mode": "unsupported_signal",
                "abnormal_return_6h": -0.02,
                "abnormal_return_24h": -0.03,
            },
            {
                "overall_label": "data_unavailable",
                "failure_mode": "data_unavailable",
                "abnormal_return_6h": None,
                "abnormal_return_24h": None,
            },
        ]
    )

    summary = build_outcome_validation_dataset_summary(records_df)

    assert summary["total_records"] == 3
    assert summary["testable_records"] == 2
    assert summary["supported_count"] == 1
    assert summary["unsupported_count"] == 1
    assert summary["data_unavailable_count"] == 1
    assert summary["support_rate"] == pytest.approx(0.5)
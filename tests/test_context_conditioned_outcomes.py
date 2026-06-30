import pandas as pd
import pytest

from src.analytics.context_conditioned_outcomes import (
    build_context_conditioned_summary,
)


def sample_context_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "record_key": "r1",
                "overall_label": "failed",
                "failure_mode": "unsupported_signal",
                "event_volatility_regime": "extreme",
                "event_liquidity_status": "stale",
                "context_bucket": "volatility_only_context",
            },
            {
                "record_key": "r2",
                "overall_label": "failed",
                "failure_mode": "unsupported_signal",
                "event_volatility_regime": "extreme",
                "event_liquidity_status": "stale",
                "context_bucket": "volatility_only_context",
            },
            {
                "record_key": "r3",
                "overall_label": "reversal",
                "failure_mode": "short_lived_reaction",
                "event_volatility_regime": "elevated",
                "event_liquidity_status": "stale",
                "context_bucket": "volatility_only_context",
            },
            {
                "record_key": "r4",
                "overall_label": "worked",
                "failure_mode": "no_failure",
                "event_volatility_regime": "extreme",
                "event_liquidity_status": "stale",
                "context_bucket": "volatility_only_context",
            },
            {
                "record_key": "r5",
                "overall_label": "data_unavailable",
                "failure_mode": "data_unavailable",
                "event_volatility_regime": "normal",
                "event_liquidity_status": "stale",
                "context_bucket": "liquidity_unavailable_context",
            },
        ]
    )


def test_build_context_conditioned_summary_groups_by_context_bucket():
    result = build_context_conditioned_summary(
        sample_context_rows(),
        group_columns=["context_bucket"],
    )

    row = result[result["group_value"] == "volatility_only_context"].iloc[0]

    assert row["group_name"] == "context_bucket"
    assert row["total_records"] == 4
    assert row["worked_count"] == 1
    assert row["failed_count"] == 2
    assert row["reversal_count"] == 1
    assert row["data_unavailable_count"] == 0
    assert row["support_rate"] == pytest.approx(0.25)
    assert row["failure_rate"] == pytest.approx(0.50)
    assert row["reversal_rate"] == pytest.approx(0.25)
    assert row["dominant_outcome"] == "failed"
    assert "failed" in row["interpretation"]


def test_build_context_conditioned_summary_groups_by_volatility_regime():
    result = build_context_conditioned_summary(
        sample_context_rows(),
        group_columns=["event_volatility_regime"],
    )

    row = result[result["group_value"] == "extreme"].iloc[0]

    assert row["group_name"] == "event_volatility_regime"
    assert row["total_records"] == 3
    assert row["worked_count"] == 1
    assert row["failed_count"] == 2
    assert row["reversal_count"] == 0
    assert row["support_rate"] == pytest.approx(1 / 3)
    assert row["dominant_outcome"] == "failed"


def test_build_context_conditioned_summary_groups_by_liquidity_status():
    result = build_context_conditioned_summary(
        sample_context_rows(),
        group_columns=["event_liquidity_status"],
    )

    row = result[result["group_value"] == "stale"].iloc[0]

    assert row["group_name"] == "event_liquidity_status"
    assert row["total_records"] == 5
    assert row["worked_count"] == 1
    assert row["failed_count"] == 2
    assert row["reversal_count"] == 1
    assert row["data_unavailable_count"] == 1


def test_build_context_conditioned_summary_returns_empty_schema_for_empty_input():
    empty = sample_context_rows().iloc[0:0]

    result = build_context_conditioned_summary(empty)

    assert list(result.columns) == [
        "group_name",
        "group_value",
        "total_records",
        "worked_count",
        "failed_count",
        "reversal_count",
        "data_unavailable_count",
        "support_rate",
        "failure_rate",
        "reversal_rate",
        "dominant_outcome",
        "interpretation",
    ]
    assert result.empty


def test_build_context_conditioned_summary_rejects_missing_required_columns():
    bad = sample_context_rows().drop(columns=["overall_label"])

    with pytest.raises(ValueError, match="Missing required columns"):
        build_context_conditioned_summary(bad)


def test_build_context_conditioned_summary_rejects_unknown_group_column():
    with pytest.raises(ValueError, match="Unknown group column"):
        build_context_conditioned_summary(
            sample_context_rows(),
            group_columns=["not_a_column"],
        )

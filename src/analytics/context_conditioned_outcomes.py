"""Context-conditioned outcome summaries for whale-flow validation records.

This module does not create new trading signals. It summarizes already validated
event-time context rows so the project can study when whale-flow signals worked,
failed, reversed, or became unavailable under different market conditions.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


REQUIRED_COLUMNS = {
    "record_key",
    "overall_label",
    "failure_mode",
    "event_volatility_regime",
    "event_liquidity_status",
    "context_bucket",
}

DEFAULT_GROUP_COLUMNS = [
    "context_bucket",
    "event_volatility_regime",
    "event_liquidity_status",
]

OUTCOME_LABELS = {
    "worked",
    "failed",
    "reversal",
    "data_unavailable",
}

OUTPUT_COLUMNS = [
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


def _missing_columns(frame: pd.DataFrame, required_columns: set[str]) -> list[str]:
    return sorted(required_columns.difference(frame.columns))


def _validate_inputs(
    context_rows: pd.DataFrame,
    group_columns: Sequence[str],
) -> None:
    missing = _missing_columns(context_rows, REQUIRED_COLUMNS)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    unknown_group_columns = [
        column for column in group_columns if column not in context_rows.columns
    ]
    if unknown_group_columns:
        raise ValueError(f"Unknown group column(s): {unknown_group_columns}")


def _safe_rate(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return count / total


def _dominant_outcome(counts: dict[str, int]) -> str:
    ordered_labels = ["failed", "worked", "reversal", "data_unavailable"]
    return max(ordered_labels, key=lambda label: counts.get(label, 0))


def _build_interpretation(
    group_name: str,
    group_value: object,
    total_records: int,
    counts: dict[str, int],
    dominant_outcome: str,
) -> str:
    return (
        f"{group_name}={group_value}: {total_records} record(s), "
        f"{counts['worked']} worked, {counts['failed']} failed, "
        f"{counts['reversal']} reversal, "
        f"{counts['data_unavailable']} data_unavailable. "
        f"Dominant outcome: {dominant_outcome}."
    )


def build_context_conditioned_summary(
    context_rows: pd.DataFrame,
    group_columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Summarize validated signal outcomes by event-time context groups.

    Parameters
    ----------
    context_rows:
        Event-time context records, usually produced by the V3 context layer.
    group_columns:
        Columns used to group the rows. By default, the function groups by
        context bucket, volatility regime, and liquidity status.

    Returns
    -------
    pandas.DataFrame
        One summary row per group value, including worked/failed/reversal counts
        and simple reliability rates.
    """

    selected_group_columns = list(group_columns or DEFAULT_GROUP_COLUMNS)
    _validate_inputs(context_rows, selected_group_columns)

    if context_rows.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    rows: list[dict[str, object]] = []

    for group_name in selected_group_columns:
        grouped = context_rows.groupby(group_name, dropna=False)

        for group_value, group_frame in grouped:
            labels = group_frame["overall_label"].astype(str)
            counts = {
                label: int((labels == label).sum())
                for label in OUTCOME_LABELS
            }

            total_records = int(len(group_frame))
            dominant_outcome = _dominant_outcome(counts)

            rows.append(
                {
                    "group_name": group_name,
                    "group_value": group_value,
                    "total_records": total_records,
                    "worked_count": counts["worked"],
                    "failed_count": counts["failed"],
                    "reversal_count": counts["reversal"],
                    "data_unavailable_count": counts["data_unavailable"],
                    "support_rate": _safe_rate(counts["worked"], total_records),
                    "failure_rate": _safe_rate(counts["failed"], total_records),
                    "reversal_rate": _safe_rate(counts["reversal"], total_records),
                    "dominant_outcome": dominant_outcome,
                    "interpretation": _build_interpretation(
                        group_name=group_name,
                        group_value=group_value,
                        total_records=total_records,
                        counts=counts,
                        dominant_outcome=dominant_outcome,
                    ),
                }
            )

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)

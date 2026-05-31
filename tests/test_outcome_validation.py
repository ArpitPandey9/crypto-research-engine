import pytest

from src.analytics.outcome_validation import (
    calculate_abnormal_return,
    calculate_return,
    label_horizon_outcome,
    summarize_overall_label,
)


def test_calculate_return_positive_move():
    result = calculate_return(event_price=100.0, future_price=105.0)

    assert result == pytest.approx(0.05)


def test_calculate_return_negative_move():
    result = calculate_return(event_price=100.0, future_price=95.0)

    assert result == pytest.approx(-0.05)


def test_calculate_return_rejects_zero_event_price():
    with pytest.raises(ValueError, match="event_price must be greater than zero"):
        calculate_return(event_price=0.0, future_price=100.0)


def test_calculate_return_rejects_negative_future_price():
    with pytest.raises(ValueError, match="future_price cannot be negative"):
        calculate_return(event_price=100.0, future_price=-1.0)


def test_calculate_abnormal_return():
    result = calculate_abnormal_return(
        actual_return=0.05,
        benchmark_return=0.03,
    )

    assert result == pytest.approx(0.02)


def test_positive_signal_with_positive_abnormal_return_worked():
    result = label_horizon_outcome(
        signal_direction="positive",
        abnormal_return=0.02,
    )

    assert result == "worked"


def test_positive_signal_with_negative_abnormal_return_failed():
    result = label_horizon_outcome(
        signal_direction="positive",
        abnormal_return=-0.02,
    )

    assert result == "failed"


def test_negative_signal_with_negative_abnormal_return_worked():
    result = label_horizon_outcome(
        signal_direction="negative",
        abnormal_return=-0.03,
    )

    assert result == "worked"


def test_negative_signal_with_positive_abnormal_return_failed():
    result = label_horizon_outcome(
        signal_direction="negative",
        abnormal_return=0.03,
    )

    assert result == "failed"


def test_zero_abnormal_return_is_inconclusive():
    result = label_horizon_outcome(
        signal_direction="positive",
        abnormal_return=0.0,
    )

    assert result == "inconclusive"


def test_missing_abnormal_return_is_data_unavailable():
    result = label_horizon_outcome(
        signal_direction="positive",
        abnormal_return=None,
    )

    assert result == "data_unavailable"


def test_label_horizon_outcome_rejects_invalid_signal_direction():
    with pytest.raises(ValueError, match="signal_direction"):
        label_horizon_outcome(
            signal_direction="flat",
            abnormal_return=0.01,
        )


def test_overall_worked_when_both_horizons_worked():
    result = summarize_overall_label(
        label_6h="worked",
        label_24h="worked",
    )

    assert result == "worked"


def test_overall_failed_when_both_horizons_failed():
    result = summarize_overall_label(
        label_6h="failed",
        label_24h="failed",
    )

    assert result == "failed"


def test_overall_reversal_when_6h_worked_and_24h_failed():
    result = summarize_overall_label(
        label_6h="worked",
        label_24h="failed",
    )

    assert result == "reversal"


def test_overall_delayed_reaction_when_6h_failed_and_24h_worked():
    result = summarize_overall_label(
        label_6h="failed",
        label_24h="worked",
    )

    assert result == "delayed_reaction"


def test_overall_inconclusive_when_any_horizon_is_inconclusive():
    result = summarize_overall_label(
        label_6h="worked",
        label_24h="inconclusive",
    )

    assert result == "inconclusive"


def test_overall_data_unavailable_when_any_horizon_missing():
    result = summarize_overall_label(
        label_6h="worked",
        label_24h="data_unavailable",
    )

    assert result == "data_unavailable"
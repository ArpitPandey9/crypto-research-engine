import pytest

from src.analytics.outcome_validation import (
    calculate_abnormal_return,
    calculate_return,
    classify_evidence_quality,
    classify_failure_mode,
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


def test_evidence_quality_strong_when_both_horizons_worked():
    result = classify_evidence_quality(
        label_6h="worked",
        label_24h="worked",
    )

    assert result == "strong"


def test_evidence_quality_strong_when_both_horizons_failed():
    result = classify_evidence_quality(
        label_6h="failed",
        label_24h="failed",
    )

    assert result == "strong"


def test_evidence_quality_mixed_when_horizons_disagree():
    result = classify_evidence_quality(
        label_6h="worked",
        label_24h="failed",
    )

    assert result == "mixed"


def test_evidence_quality_weak_when_horizon_is_inconclusive():
    result = classify_evidence_quality(
        label_6h="worked",
        label_24h="inconclusive",
    )

    assert result == "weak"


def test_evidence_quality_unavailable_when_data_is_missing():
    result = classify_evidence_quality(
        label_6h="worked",
        label_24h="data_unavailable",
    )

    assert result == "unavailable"


def test_failure_mode_no_failure_when_both_horizons_worked():
    result = classify_failure_mode(
        label_6h="worked",
        label_24h="worked",
    )

    assert result == "no_failure"


def test_failure_mode_unsupported_signal_when_both_horizons_failed():
    result = classify_failure_mode(
        label_6h="failed",
        label_24h="failed",
    )

    assert result == "unsupported_signal"


def test_failure_mode_short_lived_reaction_when_6h_worked_24h_failed():
    result = classify_failure_mode(
        label_6h="worked",
        label_24h="failed",
    )

    assert result == "short_lived_reaction"


def test_failure_mode_delayed_reaction_when_6h_failed_24h_worked():
    result = classify_failure_mode(
        label_6h="failed",
        label_24h="worked",
    )

    assert result == "delayed_reaction"


def test_failure_mode_inconclusive_evidence_when_horizon_is_inconclusive():
    result = classify_failure_mode(
        label_6h="worked",
        label_24h="inconclusive",
    )

    assert result == "inconclusive_evidence"


def test_failure_mode_data_unavailable_when_data_is_missing():
    result = classify_failure_mode(
        label_6h="worked",
        label_24h="data_unavailable",
    )

    assert result == "data_unavailable"

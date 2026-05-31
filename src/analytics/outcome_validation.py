"""Outcome validation helpers for whale-flow research.

This module contains small, testable functions used to compare a whale-flow
signal against post-signal market outcomes.

The goal is not to prove prediction.
The goal is to label whether a signal was supported, failed, reversed,
delayed, inconclusive, or unavailable inside fixed event windows.
"""

from __future__ import annotations


VALID_SIGNAL_DIRECTIONS = {"positive", "negative"}
VALID_HORIZON_LABELS = {
    "worked",
    "failed",
    "inconclusive",
    "data_unavailable",
}


def calculate_return(event_price: float, future_price: float) -> float:
    """Calculate simple return from event price to future price.

    Formula:
        return = (future_price - event_price) / event_price
    """
    if event_price <= 0:
        raise ValueError("event_price must be greater than zero.")

    if future_price < 0:
        raise ValueError("future_price cannot be negative.")

    return (future_price - event_price) / event_price


def calculate_abnormal_return(
    actual_return: float,
    benchmark_return: float,
) -> float:
    """Calculate benchmark-adjusted abnormal return.

    Formula:
        abnormal_return = actual_return - benchmark_return
    """
    return actual_return - benchmark_return


def label_horizon_outcome(
    signal_direction: str,
    abnormal_return: float | None,
    tolerance: float = 0.0,
) -> str:
    """Label one event horizon using signal direction and abnormal return.

    Positive signal:
        positive abnormal return -> worked
        negative abnormal return -> failed

    Negative signal:
        negative abnormal return -> worked
        positive abnormal return -> failed

    Near-zero abnormal return -> inconclusive
    Missing abnormal return -> data_unavailable
    """
    if signal_direction not in VALID_SIGNAL_DIRECTIONS:
        raise ValueError("signal_direction must be 'positive' or 'negative'.")

    if tolerance < 0:
        raise ValueError("tolerance cannot be negative.")

    if abnormal_return is None:
        return "data_unavailable"

    if abs(abnormal_return) <= tolerance:
        return "inconclusive"

    if signal_direction == "positive":
        return "worked" if abnormal_return > 0 else "failed"

    return "worked" if abnormal_return < 0 else "failed"


def summarize_overall_label(label_6h: str, label_24h: str) -> str:
    """Summarize 6h and 24h labels into one overall event label."""
    if label_6h not in VALID_HORIZON_LABELS:
        raise ValueError("label_6h is not a valid horizon label.")

    if label_24h not in VALID_HORIZON_LABELS:
        raise ValueError("label_24h is not a valid horizon label.")

    if "data_unavailable" in {label_6h, label_24h}:
        return "data_unavailable"

    if label_6h == "worked" and label_24h == "worked":
        return "worked"

    if label_6h == "failed" and label_24h == "failed":
        return "failed"

    if label_6h == "worked" and label_24h == "failed":
        return "reversal"

    if label_6h == "failed" and label_24h == "worked":
        return "delayed_reaction"

    return "inconclusive"
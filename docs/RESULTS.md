# Outcome Validation Results

## Purpose

This document summarizes the current public outcome-validation result for the Crypto Research Engine.

The goal is not to prove that whale-flow always works. The goal is to test whether positive ETH whale-flow becomes decision-useful after adjusting the outcome against BTC benchmark movement.

The full case-level sample is available here:

`data/samples/outcome_validation_v2_sample.csv`

## Dataset

The current V2 sample contains 11 stored outcome-validation records.

Of those records, 10 are testable and 1 is marked data_unavailable because the required forward price window was unavailable.

The validation sample focuses on positive ETH whale-flow signals.

## Method

Each signal is evaluated against ETH forward returns at two horizons:

- +6 hours
- +24 hours

The ETH return is then compared against BTC over the same horizon.

This creates a BTC-adjusted abnormal return.

A positive whale-flow signal is treated as supported only when ETH outperforms BTC on a benchmark-adjusted basis.

## Result Summary

| Metric | Value |
|---|---:|
| Stored validation records | 11 |
| Testable records | 10 |
| Worked signals | 1 |
| Failed signals | 7 |
| Reversal / short-lived reaction signals | 2 |
| Delayed reaction signals | 0 |
| Data unavailable records | 1 |
| Support rate | 10.00% |

## Interpretation

The current sample does not support a simple claim that positive ETH whale-flow reliably predicts durable ETH outperformance.

The strongest early finding is that positive whale-flow appears benchmark-sensitive and often short-lived in this sample.

Two records showed short-lived reaction: the signal was supported at +6h but failed by +24h. This suggests that some whale-flow events may create short-term movement without producing durable benchmark-adjusted outperformance.

## Failure Modes

The most common failure mode is unsupported_signal.

This means the signal was testable, but ETH did not outperform BTC after the signal.

The second important failure mode is short_lived_reaction.

This means the signal showed early support but failed over the longer +24h horizon.

## Research Conclusion

Positive ETH whale-flow should not be treated as a standalone predictive signal based on this sample.

The next research step is to attach event-time liquidity and volatility context to each validation record.

That would allow the project to test whether worked, failed, and short-lived signals differ by liquidity absorption capacity, volatility regime, or broader market structure.

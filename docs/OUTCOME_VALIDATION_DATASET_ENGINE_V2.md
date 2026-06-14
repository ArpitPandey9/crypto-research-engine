# Outcome Validation Dataset Engine V2

## Purpose

The purpose of this engine is to move the whale-flow mechanism layer from a single validated example into a small but structured research dataset.

The engine does not try to prove that whale-flow always works. Instead, it records when whale-flow signals are supported, unsupported, inconclusive, or untestable due to missing data.

The core research question is:

> Under what market conditions does whale-flow become decision-useful rather than noise?

## Why V2 Exists

A single outcome validation sample is useful as a proof of method, but it is not enough to support a research conclusion.

V2 is designed to store many validated whale-flow events with consistent fields, so the project can analyze signal reliability across volatility regimes, liquidity contexts, abnormal returns, evidence quality, and failure modes.

## Research Standard

This engine follows four rules:

1. Real data only.
2. No invented outcomes.
3. Missing data must be labeled honestly.
4. Every conclusion must be traceable back to a stored validation record.

## Validation Record Fields

Each validated signal should store:

- event_id
- asset
- signal_timestamp
- signal_direction
- rolling_net_flow_usd
- min_flow_usd
- window_hours
- volatility_regime
- liquidity_context
- size_ratio
- benchmark_asset
- asset_return_6h
- benchmark_return_6h
- abnormal_return_6h
- asset_return_24h
- benchmark_return_24h
- abnormal_return_24h
- outcome_label
- evidence_quality
- failure_mode
- data_quality_status
- validation_notes
- created_at

## Outcome Labels

Supported:

The signal direction is supported by the benchmark-adjusted outcome.

Unsupported:

The signal direction is contradicted by the benchmark-adjusted outcome.

Inconclusive:

The outcome is too weak, mixed, or unclear to support a strong conclusion.

Data Unavailable:

The signal cannot be properly validated because required real data is missing.

## Evidence Quality

Strong:

Enough data exists, the abnormal return is clear, and the validation result is interpretable.

Moderate:

Enough data exists, but the result is weaker, mixed, or less decisive.

Weak:

The data exists but is noisy, marginal, or difficult to interpret.

Unavailable:

Required data is missing.

## Failure Modes

unsupported_signal:

The signal was testable but not supported by the observed outcome.

benchmark_outperformance:

The asset may have moved positively, but underperformed the benchmark.

insufficient_price_data:

The required forward price window was unavailable.

liquidity_context_unavailable:

The event could not be linked to usable liquidity context.

volatility_context_unavailable:

The event could not be linked to volatility regime data.

mixed_horizon_result:

The 6h and 24h outcomes disagree.

unknown:

The failure reason cannot yet be classified.

## Research Outputs

The engine should produce summary statistics such as:

- total validated signals
- supported count
- unsupported count
- inconclusive count
- data unavailable count
- support rate
- average abnormal return
- results by volatility regime
- results by liquidity context
- most common failure modes

## Intended Next Research Note

After enough records are collected, the next research note should answer:

> Does whale-flow reliability change across volatility and liquidity regimes?

The target is not a perfect model. The target is a defensible research dataset that shows where the signal works, where it breaks, and why.

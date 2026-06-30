# Context-Conditioned Outcome Analysis Plan

## Purpose

The project already validates whether positive ETH whale-flow signals worked, failed, reversed, or became unavailable after BTC benchmark adjustment.

The next research step is to explain signal reliability by attaching stronger event-time market context.

The main research question is:

> Under which event-time market conditions does positive ETH whale-flow become decision-useful, short-lived, or unsupported?

## Current State

The current V2 outcome-validation dataset shows that positive ETH whale-flow did not reliably produce durable BTC-adjusted outperformance.

The V3 event-time context sample shows that volatility context is available for most records, but liquidity context is mostly stale or unavailable.

This means the project can currently discuss volatility context, but it cannot yet make strong liquidity-impact claims.

## Problem

A whale-flow signal alone is not enough.

A positive signal can fail because:

- ETH moved with the broader crypto market instead of outperforming BTC
- the market was in an elevated or extreme volatility regime
- liquidity was too deep for the flow to matter
- liquidity was too thin and the reaction was short-lived
- liquidity data was stale or unavailable, making impact claims unsafe

The project should avoid fake precision. If event-time liquidity is stale, missing, or from the future, flow-to-liquidity ratio must remain unavailable.

## V4 Goal

V4 will move the project from signal validation to context-conditioned signal reliability.

It will test whether failed or reversal whale-flow outcomes are associated with event-time volatility and usable liquidity context.

## Data Inputs

V4 should use:

- `outcome_validation_records`
- `historical_prices`
- `dex_pool_depths`
- `event_time_context_v3_sample.csv`
- newly collected or backfilled event-time liquidity snapshots, if available

## Core Rules

1. Use only data available at or before the event timestamp.
2. Never use future liquidity snapshots.
3. Do not calculate flow-to-liquidity ratio from stale liquidity.
4. If liquidity is missing, mark liquidity context as unavailable.
5. If liquidity is stale, mark it as stale and leave impact ratio blank.
6. Keep failed signals visible instead of hiding them.
7. Treat signal failure as research evidence, not as project failure.

## Proposed Output

The V4 output should produce a grouped context-conditioned outcome summary with columns such as:

- `group_name`
- `group_value`
- `total_records`
- `worked_count`
- `failed_count`
- `reversal_count`
- `data_unavailable_count`
- `support_rate`
- `failure_rate`
- `reversal_rate`
- `dominant_outcome`
- `interpretation`

This grouped table should be generated from the V3 event-time context records. It should summarize reliability patterns without creating new trading signals or hiding failed outcomes.

## Research Interpretation

The goal is not to prove that whale-flow always predicts price.

The goal is to classify when whale-flow is:

- supported
- unsupported
- short-lived
- untestable because of missing data
- unsafe to interpret because liquidity context is stale

## Expected Research Value

This iteration makes the project more institutionally useful because it does not stop at showing a signal.

It asks whether the signal survives benchmark adjustment and whether market context explains the result.

The project becomes stronger because it separates:

- signal generation
- outcome validation
- volatility context
- liquidity context
- data availability
- honest limitations

## Next Implementation Steps

1. Inspect existing V3 event-time context logic.
2. Identify freshness threshold used for liquidity.
3. Build a context-conditioned outcome summary.
4. Group results by volatility regime and liquidity status.
5. Keep liquidity-impact ratios unavailable unless liquidity is fresh.
6. Export a public V4 sample CSV.
7. Add tests for stale, missing, future, and fresh liquidity cases.
8. Write a short V4 research note with honest findings.

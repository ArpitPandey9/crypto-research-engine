# Event-Time Market Context V3

## Purpose

This layer attaches market context to each stored outcome-validation record.

The goal is to explain whether worked, failed, and short-lived whale-flow signals happened under different volatility and liquidity conditions.

This layer does not create new whale-flow signals. It only enriches existing validation records with event-time context.

## Method

For each validation record, the module uses only data available at or before the event timestamp.

Volatility context is built from prior historical price data for the target price asset.

Liquidity context is built from prior DEX pool-depth snapshots when available.

Future liquidity snapshots are not used.

Stale liquidity snapshots are not used to calculate flow-to-liquidity ratios.

## Context Labels

`context_unavailable` means both volatility and usable liquidity context are unavailable.

`volatility_only_context` means volatility context is available, but liquidity is stale or unavailable. In this case, the project does not calculate a flow-to-liquidity ratio.

`liquidity_unavailable_context` means volatility may be available, but liquidity is not fresh enough to support impact-ratio analysis.

`normal_absorption_context`, `mixed_market_context`, and `fragile_market_context` are reserved for cases where fresh liquidity exists and flow-to-liquidity analysis can be performed.

## Current V3 Finding

The current V3 sample contains 11 records.

Nine records have volatility-only context. One record has unavailable context. One record has liquidity-unavailable context.

This means the current sample can support volatility-context interpretation, but it cannot yet support strong liquidity-impact claims.

The next improvement is to add historical liquidity backfill or a transparent liquidity proxy so that stale liquidity does not limit event-time interpretation.

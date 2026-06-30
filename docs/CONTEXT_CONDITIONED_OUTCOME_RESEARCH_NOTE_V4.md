# Context-Conditioned Outcome Research Note V4

## Hypothesis

The project originally tested whether positive ETH whale-flow signals could explain short-term ETH behavior after adjusting for broad crypto-market movement using BTC as a benchmark. Earlier validation showed that the signal was not reliably durable on its own. V4 asks a narrower and more useful question:

> Does whale-flow reliability change when outcomes are grouped by event-time volatility and liquidity context?

## Method

V4 uses the existing outcome-validation records and the V3 event-time context layer. Each validated whale-flow event is grouped by context bucket, volatility regime, and liquidity status. The analysis keeps worked, failed, reversal, and data-unavailable outcomes visible instead of hiding weak results.

The core research discipline is prior-only evidence. The system should use only information available at or before the event timestamp. Future liquidity snapshots are rejected. Stale liquidity snapshots are not used to calculate flow-to-liquidity ratios. If liquidity is missing or stale, the project leaves impact-ratio claims unavailable instead of creating false precision.

## Findings

The current V4 sample supports one careful conclusion: positive ETH whale-flow should not be treated as a standalone durable signal. The prior validation set already showed that many positive whale-flow cases failed after BTC benchmark adjustment, with some short-lived reversals. V4 adds context by showing where those outcomes sit across volatility and liquidity conditions.

The most important finding is not that liquidity explains the result. It does not yet. The current event-time context shows that volatility context is available for most records, but liquidity context is often stale or unavailable. Therefore, the project can discuss volatility-regime context, but it cannot honestly claim that DEX pool depth absorbed, amplified, or invalidated the whale-flow signal.

## Interpretation

This is a stronger research result than a forced “successful signal.” The project now separates signal generation, outcome validation, market context, data availability, and research limitations. That is closer to how an institutional research workflow should behave: weak or failed signals are treated as evidence, not hidden.

The current interpretation is that positive whale-flow may sometimes align with short-window movement, but it is not yet robust enough to be used as a durable directional signal. Context matters, and missing liquidity context remains the main blocker to stronger mechanism claims.

## Limitations

This sample is still small and focused on positive ETH whale-flow. It does not prove causality, does not confirm whale intent, does not provide financial advice, and does not establish production trading readiness. BTC benchmark adjustment is useful but not exhaustive. Liquidity analysis remains limited until event-time liquidity can be backfilled or proxied in a reproducible way.

## Next Improvement

The next research upgrade should be historical liquidity backfill or a transparent liquidity proxy. Once fresher event-time liquidity exists, the project can test whether failures and reversals are linked to pool-depth absorption, fragile liquidity, or volatility-driven noise.

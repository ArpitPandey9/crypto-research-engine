# Outcome Validation Research Note V2

## Hypothesis

Positive ETH whale-flow may indicate future ETH outperformance when compared against BTC benchmark movement.

## Dataset

This note summarizes the first small outcome-validation dataset produced by the project’s V2 validation engine.

The dataset contains 11 stored validation records, of which 10 are testable. One record is marked data_unavailable because the required forward price window was not available.

All records are based on real stored whale-flow observations and historical price data from the local SQLite database.

## Signal Tested

The tested signal is positive ETH rolling net whale-flow over a 12-hour window.

Each signal is evaluated against ETH forward returns at +6h and +24h, then adjusted against BTC benchmark returns over the same horizons.

A signal is considered supported only when ETH shows positive benchmark-adjusted outperformance.

## Result

Across 10 testable records:

- 1 worked
- 7 failed
- 2 reversed after short-term support
- 0 delayed reactions

The current support rate is 10.00%.

The most common failure mode is unsupported_signal. Two records are classified as short_lived_reaction because the signal was supported at +6h but failed by +24h.

## Interpretation

The early evidence does not support a simple claim that positive ETH whale-flow reliably predicts durable ETH outperformance.

The more useful finding is that whale-flow appears benchmark-sensitive and often short-lived in this sample. Some whale-flow events may create short-term reaction, but that reaction does not necessarily persist after BTC-adjusted comparison.

This is important because it shifts the research question away from “does whale-flow work?” and toward “under what market conditions does whale-flow become decision-useful rather than noise?”

## Limitations

This is still a small sample.

The current dataset focuses on ETH positive whale-flow only. It does not yet attach event-time liquidity context, volatility regime, exchange-flow classification, or pool-depth absorption analysis to each validation record.

The result should be treated as early research evidence, not a trading signal or financial advice.

## Next Improvement

The next research step is to attach event-time liquidity and volatility context to each validation record.

That would allow the project to test whether failed, worked, and short-lived whale-flow signals differ by market regime, pool-depth absorption capacity, or volatility environment.

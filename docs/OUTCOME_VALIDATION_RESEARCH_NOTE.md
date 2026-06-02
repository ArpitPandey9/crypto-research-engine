# Outcome Validation Research Note v1

## Hypothesis

Large positive ETH whale-flow pressure may indicate short-term upside pressure when the flow reflects meaningful market activity rather than noise. However, the signal should not be treated as predictive unless post-signal outcomes support it after adjusting for broader market movement.

## Signal Tested

The first validation sample tested a positive ETH whale-flow signal generated from the local SQLite whale-flow dataset. The signal was based on rolling net whale flow and then evaluated against +6h and +24h ETH outcomes.

To avoid overclaiming, the result was benchmark-adjusted against BTC. This means the system did not only ask whether ETH moved up or down. It asked whether ETH outperformed or underperformed BTC over the same window.

## Result

The sample produced a positive ETH whale-flow signal with rolling net flow of $1,899,322.81.

At the +6h horizon, ETH had a positive raw return, but BTC performed better during the same period. After benchmark adjustment, ETH underperformed BTC by 0.1946%.

At the +24h horizon, ETH again underperformed BTC after benchmark adjustment, with abnormal return of -0.0977%.

Both horizons were therefore labeled as failed. The overall label was failed, the evidence quality was strong, and the failure mode was classified as unsupported_signal.

## Interpretation

This result does not mean the whale-flow framework is useless. It means this specific positive signal was not supported by the observed market outcome after adjusting for broad crypto market movement.

That is an important research outcome. A weak dashboard might force every whale-flow signal to look meaningful. A stronger research system should also identify when a signal breaks.

In this case, the system produced a clear signal, tested it against real outcomes, adjusted for BTC, and honestly recorded that the signal was unsupported.

## Limitations

This is only a first small validation sample. It does not prove causality, does not confirm whale intent, and does not establish production trading readiness. Liquidity context was also not attached to this event because the available DEX pool-depth snapshot was not event-time aligned with the whale event.

## Next Improvement

The next improvement is to repeat this validation across more whale-flow events and compare outcomes across volatility regimes, liquidity conditions, and flow-context classifications. The goal is to identify when whale-flow pressure becomes decision-useful, when it becomes noisy, and when it should be ignored.

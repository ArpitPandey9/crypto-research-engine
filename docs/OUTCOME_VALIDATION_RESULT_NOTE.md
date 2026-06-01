# Outcome Validation Result Note v1

This note records the first real benchmark-adjusted outcome-validation result from the local SQLite whale-flow dataset.

The goal is not to prove a guaranteed trading signal. The goal is to test whether a whale-flow signal was supported by observed +6h and +24h market outcomes after adjusting for broad BTC benchmark movement.

---

## 1. Validation setup

Command used:

`python scripts/run_outcome_validation.py --target-asset ETH --benchmark-asset BTC --window-hours 12 --min-flow-usd 0`

Validation design:

- target asset: ETH
- benchmark asset: BTC
- signal window: 12 hours
- outcome windows: +6h and +24h
- benchmark adjustment: abnormal return = actual return - BTC benchmark return
- local source: SQLite whale-data vault

---

## 2. First real ETH sample result

| Field | Result |
|---|---:|
| Rolling net flow | $1,899,322.81 |
| +6h actual return | 0.7344% |
| +6h BTC benchmark return | 0.9290% |
| +6h abnormal return | -0.1946% |
| +6h label | failed |
| +24h actual return | -0.2621% |
| +24h BTC benchmark return | -0.1644% |
| +24h abnormal return | -0.0977% |
| +24h label | failed |
| Overall label | failed |
| Evidence quality | strong |
| Failure mode | unsupported_signal |

---

## 3. Interpretation

The positive ETH whale-flow signal was not supported in this sample after BTC benchmark adjustment.

At +6h, ETH was positive in raw actual-return terms, but BTC performed better during the same window. This means ETH underperformed the benchmark after adjustment.

At +24h, ETH also underperformed BTC after benchmark adjustment.

Because both +6h and +24h labels failed, the evidence quality is strong, but it is strong evidence against the signal.

The correct failure-mode interpretation is `unsupported_signal`.

This means the signal was clear, the outcome evidence was clear, but the market outcome did not support the signal direction.

---

## 4. What this does not claim

This result does not claim guaranteed prediction, confirmed whale intent, financial advice, production trading readiness, or causality between whale flow and price movement.

It only claims that this specific ETH whale-flow signal was tested against real post-signal outcomes and was not supported after BTC benchmark adjustment.

---

## 5. Liquidity limitation

Liquidity was not attached to this event result because the current DEX pool-depth snapshot is not event-time aligned with the whale event.

Using a later liquidity snapshot for an earlier whale event could create misleading research evidence.

Until event-time aligned liquidity is available, liquidity context should be marked as unavailable for this validation result.

---

## 6. Research conclusion

This is useful because the framework did not force a bullish conclusion.

The system generated a positive whale-flow signal, tested it against actual +6h and +24h outcomes, adjusted those outcomes against BTC benchmark movement, and honestly classified the result as failed with strong evidence and an `unsupported_signal` failure mode.

This moves the project from a plausible signal dashboard toward a tested research framework.

# Causal Remediation Result V5

## Purpose

This note records the real-data result of the causal-timing remediation applied after an institutional audit of the Crypto Research Engine.

The audit identified two weaknesses in the earlier methodology:

1. an hourly Binance close could be attached to a whale transfer that occurred before that close was available; and
2. the shifted close-to-close backtest could use the same close both to finalize a signal and as the starting price of the next measured return.

V5 preserves the earlier V1/V2 outputs as historical methodology artifacts and introduces explicit market-data availability, signal-availability, and next-open execution semantics for new research.

## Real-data verification

The canonical SQLite research database was backed up before mutation and then backfilled from Binance using the causal price schema.

Post-backfill checks:

- SQLite integrity: `ok`
- historical price rows: 2,562
- ETH price rows: 1,281
- BTC price rows: 1,281
- enriched whale rows: 1,599
- missing event price values: 0
- missing normalized USD volumes: 0
- negative valuation lags: 0

The previously investigated 2026-04-23 ETH transfer was revalued using the latest completed hourly close available before the transfer, rather than the still-open same-hour candle close.

## Controlled backtest comparison

Parameters:

- target asset: ETH
- whale-flow window: 36 hours
- minimum flow threshold: $10,000
- transaction cost: 0.15%
- same current data and same whale-flow signal frame on both sides

| Metric | Legacy close-to-close | V5 causal next-open | V5 - legacy |
|---|---:|---:|---:|
| Research rows | 1,281 | 1,281 | 0 |
| Trades | 13 | 13 | 0 |
| Buy-and-hold equity | 0.787198x | 0.770693x | -0.016505x |
| Strategy net equity | 1.022424x | 1.005253x | -0.017172x |
| Strategy minus buy-and-hold | 0.235227x | 0.234560x | -0.000667x |

The V5 audit reported zero causal execution invariant failures.

The key interpretation is not that the legacy result was fabricated; it is that its execution convention was less conservative. After imposing explicit next-open execution, the net strategy result is lower while the measured strategy-minus-buy-and-hold difference remains close to the legacy estimate.

## Outcome-validation comparison

The stored legacy V2 dataset contained 11 records:

- 7 failed
- 2 reversal
- 1 worked
- 1 data-unavailable

The fresh causal V5/V3 recomputation also produced 11 signal cases:

- 7 failed
- 2 reversal
- 2 worked
- 0 data-unavailable

All 11 historical signal buckets matched after accounting for the one-hour difference between the legacy bucket-start label and V5 `signal_available_at`.

Ten cases kept the same overall label. The 2026-06-14 13:00 legacy bucket changed from `data_unavailable` to `worked` because the causal historical-price backfill supplied the previously missing forward market-data window.

The fresh causal support rate is therefore:

`2 / 11 = 18.18%`

The earlier public V2 support rate of 10.00% remains valid **for the frozen V2 artifact and its original data availability**. It should not be presented as the current causal-methodology result.

## Research conclusion

The remediation changes one case-level label and improves data lineage and execution discipline, but it does not justify a strong predictive claim.

Only 2 of 11 fresh causal cases are classified as worked, while 7 fail and 2 reverse after short-term support. The sample therefore still does not support positive ETH whale-flow as a reliable standalone predictor of durable ETH outperformance versus BTC.

The more defensible conclusion is that whale-flow behavior is conditional and should be interpreted together with volatility, liquidity, exchange-flow classification, and market structure.

## Release discipline

- Legacy V1/V2 samples and notes are preserved rather than overwritten.
- New outcome records carry methodology version and explicit signal timing.
- Historical prices are backfilled/upserted instead of destructively replaced.
- Whale valuation uses only prices available at or before the transfer timestamp.
- New backtests use next-open execution after signal availability.
- Prior-only event context uses market-data availability timestamps.
- WBTC remains unvalidated where real whale-event data is absent; no synthetic strategy result is generated.

This note documents methodology evolution rather than erasing the earlier result.

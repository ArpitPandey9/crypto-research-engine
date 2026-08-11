# Causal Time Semantics V5

## Why this version exists

An institutional audit identified two timing weaknesses in the earlier research path:

1. Binance hourly close prices were stored under candle-open timestamps and could therefore be attached to whale transfers that occurred before that close was known.
2. The legacy backtest shifted signals by one row but used the same hourly close that finalized the signal as the starting price of the next close-to-close return.

The earlier outputs remain historical artifacts. V5 does not silently rewrite them.

## Price-data contract

New Binance rows preserve:

- `open_time`
- `close_time`
- `price_available_at`
- `open_price`
- `high_price`
- `low_price`
- `close_price`
- backward-compatible `timestamp` (bucket start)
- backward-compatible `price_usd` (bucket close)
- `source`

`price_available_at` is the exact hourly boundary immediately after Binance's final millisecond of the candle.

Historical prices are upserted on `(asset_type, timestamp)` instead of replacing the entire table. This preserves older bars needed to reproduce historical events.

## Causal whale normalization

A whale transfer may use only the latest price whose `price_available_at <= transfer_timestamp`.

The enriched event stores:

- `valuation_price_time`
- `valuation_lag_seconds`
- `valuation_method`

For ETH/WBTC, the default method is `last_completed_binance_hourly_close`. A negative valuation lag is a hard failure.

## Signal timing

Each hourly research row carries:

- `bucket_start`
- `bucket_end`
- `signal_available_at`

The legacy `timestamp` remains a bucket-start alias for backward compatibility. It must not be interpreted as the time the completed-hour signal was already known.

## Backtest execution

The V5 causal backtest:

1. finalizes bucket `t` at `signal_available_at`,
2. enters from the next bar open,
3. measures return from that open to the following open,
4. verifies `entry_time >= source_signal_available_at` for every active position,
5. applies transaction cost when the position changes.

The legacy close-to-close shifted helper remains in code only to reproduce historical methodology.

## Event-time context

Prior-only context uses the same availability contract. Volatility history includes only market prices whose `price_available_at <= event_timestamp`, while liquidity continues to require `fetched_at_utc <= event_timestamp`. This prevents an hourly close from entering context before that close was actually observable.

## Outcome validation

New outcome-validation rows use `signal_available_at` as the event-study anchor and store:

- `methodology_version`
- `signal_bucket_start`
- `signal_available_at`

Record keys include methodology version so V3/V5 results cannot overwrite legacy V1/V2 records.

## Reproducibility rule

Historical research artifacts are versioned, not silently replaced. New claims must identify the methodology version used to generate them.

## Verified real-data remediation result

The V5 causal path was re-run against the canonical local SQLite research database after a real Binance backfill covering the full whale-event period.

Verification results:

- `historical_prices`: 2,562 rows (1,281 ETH + 1,281 BTC)
- `enriched_whales`: 1,599 rows
- missing `price_usd`: 0
- missing `true_usd_volume`: 0
- negative valuation lags: 0
- causal dashboard invariant failures: 0
- full project coverage after remediation: 91%

A controlled execution comparison used the same current data and signal frame with a 36-hour whale-flow window, $10,000 minimum flow threshold, and 0.15% transaction cost:

| Metric | Legacy close-to-close | V5 causal next-open |
|---|---:|---:|
| Research rows | 1,281 | 1,281 |
| Trades | 13 | 13 |
| Buy-and-hold equity | 0.787198x | 0.770693x |
| Strategy net equity | 1.022424x | 1.005253x |
| Strategy minus buy-and-hold | 0.235227x | 0.234560x |

The causal execution correction reduced strategy net equity by `0.017172x` and the strategy-minus-buy-and-hold difference by `0.000667x`; trade count was unchanged. The corrected path recorded zero causal execution invariant failures.

The outcome-validation comparison also matched all 11 historical signal buckets after adjusting the legacy bucket-start label to the V5 signal-availability timestamp. Ten cases retained the same overall label. One previously `data_unavailable` case became `worked` after the historical price backfill made the required forward window available.

Fresh causal outcome counts are therefore:

- 11 testable records
- 2 worked
- 7 failed
- 2 reversal / short-lived reaction
- 0 data-unavailable
- support rate: 18.18%

This does **not** reverse the earlier research conclusion. With only 2 of 11 cases classified as worked, the sample still does not support treating positive ETH whale-flow as a reliable standalone predictor of durable BTC-adjusted outperformance. What changed is the timing discipline, data availability, and one case-level classification—not the need for a cautious interpretation.

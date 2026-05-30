# Outcome Validation Plan v1

This note defines how I will validate whether whale-flow context classifications line up with actual market outcomes.

The goal is not to prove a guaranteed trading signal.

The goal is to move from a plausible whale-flow framework to a small tested framework.

---

## 1. Why this validation exists

The current project already builds whale-flow signals, adds liquidity context, detects volatility regime, and audits dashboard numbers.

The next step is to test whether the signal classifications are actually supported by post-signal behavior.

This means checking what happened after each whale-flow event instead of only saying that the signal sounds plausible.

---

## 2. Main validation question

For each whale-flow event:

> Did the asset move in a way that supports the signal after 6 hours and 24 hours?

A stronger version of the question is:

> Did the asset move more or less than the BTC benchmark after adjusting for broad market movement?

---

## 3. Event definition

An event is a timestamp where the system produces a meaningful whale-flow signal.

Each event should include:

* event time
* asset
* signal direction
* whale-flow value in USD
* pool depth in USD if available
* size ratio if available
* volatility regime if available
* flow-context classification

---

## 4. Event windows

The first validation windows are:

* +6 hours
* +24 hours

The +6h window captures short-term market reaction.

The +24h window checks whether the reaction persisted, reversed, or became inconclusive.

---

## 5. Actual return

Actual return measures how the target asset moved after the signal.

Formula:

```text
actual_return = (future_asset_price - event_asset_price) / event_asset_price
```

Actual return answers:

> What happened to the asset itself?

---

## 6. Benchmark return

Benchmark return measures how BTC or the broader crypto market moved during the same window.

Formula:

```text
benchmark_return = (future_benchmark_price - event_benchmark_price) / event_benchmark_price
```

Benchmark return answers:

> What was the market doing during the same period?

For the first version, BTC can be used as the simple benchmark.

---

## 7. Abnormal return

Abnormal return adjusts the asset return against the benchmark return.

Formula:

```text
abnormal_return = actual_return - benchmark_return
```

Abnormal return answers:

> Did the asset move more or less than the benchmark?

This helps avoid overclaiming.

Example:

```text
ETH actual return = +5%
BTC benchmark return = +3%

abnormal return = +5% - +3% = +2%
```

This means ETH outperformed BTC by 2 percentage points.

---

## 8. Outcome labels

Each event should receive horizon-level labels and an overall label.

Possible horizon labels:

* worked
* failed
* reversed
* delayed_reaction
* inconclusive
* data_unavailable

Possible overall labels:

* worked
* failed
* reversal
* delayed_reaction
* inconclusive
* data_unavailable

---

## 9. Simple labeling logic

For a positive signal:

```text
positive actual return        -> actual-return support
positive abnormal return      -> stronger benchmark-adjusted support
negative abnormal return      -> weak or unsupported relative signal
```

For a negative signal:

```text
negative actual return        -> actual-return support
negative abnormal return      -> stronger benchmark-adjusted support
positive abnormal return      -> weak or unsupported relative signal
```

If +6h and +24h disagree, the overall label should usually be inconclusive or reversal.

---

## 10. Validation table columns

The first validation table should include:

```text
event_time
asset
signal_direction
flow_context
volatility_regime
pool_depth_usd
whale_flow_usd
size_ratio
event_price
price_6h
price_24h
actual_return_6h
actual_return_24h
benchmark_price_event
benchmark_price_6h
benchmark_price_24h
benchmark_return_6h
benchmark_return_24h
abnormal_return_6h
abnormal_return_24h
label_6h
label_24h
overall_label
notes
```

---

## 11. Research-note output

After creating a small validation sample, the repo should include a short 300-500 word research note.

The note should include:

* hypothesis
* signal tested
* sample size
* where the signal worked
* where it failed
* where evidence was inconclusive
* limitations
* next improvement

---

## 12. Important limitations

This validation does not claim:

* guaranteed prediction
* confirmed whale intent
* production trading readiness
* financial advice
* causality

It only tests whether whale-flow context classifications line up with observed post-signal outcomes.

---

## 13. Target end state

The target is to make the whale-flow framework more honest, testable, and decision-useful.

The project should be able to say:

> This signal worked in these conditions, failed in these conditions, and should be ignored when evidence is weak.

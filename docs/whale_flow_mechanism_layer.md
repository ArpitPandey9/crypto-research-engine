# Whale-Flow Mechanism Layer

## Purpose

The current whale-flow system detects and analyzes large on-chain value movements. However, whale-flow alone is not enough to create a decision-useful research signal.

A large transfer only tells us that value moved. It does not prove why the value moved, whether the movement represents sell pressure, whether the market can absorb the flow, or whether the signal is reliable in the current market regime.

This document defines the next research layer for the Crypto Research Engine: the **Whale-Flow Mechanism Layer**.

The goal of this layer is to move from simple whale-flow tracking toward mechanism-based interpretation.

Instead of only asking:

> Did a whale move large value?

this layer asks:

> Where did the flow go, how strong is the evidence, can the market absorb it, what risk flag should be shown, and how reliable is the signal?

## Research Question

Can whale-flow become more decision-useful when combined with liquidity depth, flow context, evidence confidence, and volatility regime?

More specifically:

- Does the flow look like exchange inflow, exchange outflow, DEX interaction, wallet-to-wallet movement, bridge movement, or unknown movement?
- Is the whale-flow large relative to available pool depth or liquidity?
- Is the market likely to absorb the flow, or could the flow create high price impact?
- Is the signal reliable, or is the current market regime too noisy?
- What warning should the dashboard show to the researcher?

## Why Whale-Flow Alone Is Not Enough

Whale-flow alone tells us that large value moved, but it does not explain the mechanism behind the movement.

For example, a large ETH transfer could represent:

- possible sell-pressure preparation,
- exchange withdrawal,
- custody movement,
- internal wallet reshuffling,
- OTC settlement,
- cross-chain bridge movement,
- DeFi protocol interaction,
- or an unknown movement with unclear intent.

Because of this, the system should not treat every whale transfer as a direct buy or sell signal.

The project must separate:

- **movement**: large value moved,
- **context**: where the value moved,
- **evidence**: how strong the interpretation is,
- **liquidity impact**: whether the market can absorb it,
- **risk flag**: what the researcher should be careful about,
- **reliability**: whether the signal is useful in the current regime.

## Mechanism: Whale-Flow + Liquidity Depth

The core idea of this layer is that whale-flow should not be interpreted in isolation.

A large transfer may look important, but its market impact depends on whether the available liquidity can absorb that flow.

To estimate this, the system introduces a simple first-pass mechanism metric:

```text
size_ratio = whale_flow_usd / pool_depth_usd
```

The size ratio compares the dollar value of whale-flow against the available liquidity or pool depth.

A low size ratio means the flow is small relative to liquidity. In this case, the market may absorb the flow without major price impact.

A high or extreme size ratio means the flow is large relative to liquidity. In this case, the market may not absorb the flow smoothly, and the dashboard should warn about possible price-impact risk.

This does not mean the whale definitely caused a price move. It only means the flow is large enough relative to liquidity that the researcher should treat it as a possible market-structure risk.

### Initial Size-Ratio Heuristic

The first version of the system will use a transparent heuristic:

| Size Ratio | Liquidity Interpretation | Risk Flag |
|---:|---|---|
| `< 1%` | Flow is small relative to liquidity | Low Price-Impact Risk / Flow Likely Absorbed |
| `1% – 5%` | Flow is noticeable but may still be absorbed | Medium Price-Impact Risk |
| `5% – 10%` | Flow is large relative to liquidity | High Price-Impact Risk |
| `> 10%` | Flow is very large relative to liquidity | Extreme Price-Impact Risk |

These thresholds are not universal trading laws. They are an explainable starting point for research and must be stress-tested later.

The purpose of the heuristic is not to predict price perfectly. The purpose is to make the dashboard more decision-useful by showing whether a whale-flow signal appears in a strong-liquidity or weak-liquidity environment.

## Flow Context Classification

The mechanism layer must classify the context of each whale-flow event before assigning interpretation.

A transfer is not automatically a buy or sell signal. The meaning depends on where the value moved and what evidence is available.

The first version of the system will use a transparent flow-context framework:

| Flow Context | Possible Interpretation | Evidence Confidence |
|---|---|---|
| Exchange Inflow | Possible sell-pressure preparation | Medium |
| Exchange Outflow | Possible withdrawal, custody movement, or accumulation | Medium |
| DEX Interaction | Protocol-level market action | High |
| Bridge Movement | Cross-chain movement, not necessarily direct market pressure | Medium |
| Wallet-to-Wallet | Unknown intent or possible internal movement | Low |
| Unknown | Insufficient context | Low |

These labels are intentionally cautious.

For example, an exchange inflow may indicate possible sell-pressure preparation, but it does not prove that the whale sold. The transfer could also be related to custody, collateral movement, OTC settlement, or internal operations.

Similarly, a wallet-to-wallet transfer should usually receive a low-confidence interpretation because the system cannot reliably infer intent from movement alone.

A DEX interaction provides stronger evidence than a generic wallet transfer because it indicates interaction with a known protocol, router, or pool. However, even DEX interaction should not be treated as perfect intent certainty. It may represent a swap, routing path, arbitrage, rebalancing, or liquidity-management activity.

The system should therefore separate:

- **flow context**: where the value moved,
- **intent label**: what the movement may suggest,
- **confidence**: how strong the evidence is,
- **reason**: why the dashboard assigned that label.

## Risk Flags

A risk flag is a dashboard warning label. It does not only say whether a signal is good or bad. It tells the researcher what kind of risk or context should be noticed before interpreting the whale-flow event.

The system should avoid generic labels such as "high risk" without explanation.

Instead, each risk flag should include:

- **risk type**: what kind of warning is being shown,
- **severity**: how strong the warning is,
- **reason**: why the warning was assigned.

The first version of the system will use the following risk-flag types:

| Risk Flag | Meaning |
|---|---|
| Low Price-Impact Risk / Flow Likely Absorbed | The flow is small relative to liquidity, so the market may absorb it smoothly |
| Medium Price-Impact Risk | The flow is noticeable relative to liquidity, but may still be absorbed |
| High Price-Impact Risk | The flow is large relative to liquidity and may create meaningful market impact |
| Extreme Price-Impact Risk | The flow is very large relative to liquidity and may create severe price-impact risk |
| Possible Sell-Pressure Preparation | The flow moved toward an exchange-labeled destination |
| Possible Custody / Accumulation Movement | The flow moved out of an exchange-labeled source |
| Intent Unknown | The system cannot confidently infer why the transfer happened |
| Signal May Be Noisy | The market regime is volatile enough that the signal may be difficult to interpret |
| Execution Fragility | The estimated flow size may create high slippage or unstable execution conditions |

Risk flags should be evidence-backed.

For example, the dashboard should not only show:

> High Risk

It should show:

> Extreme Price-Impact Risk: whale-flow is large relative to pool depth, so the market may not absorb it smoothly.

This makes the dashboard explainable instead of black-box.

## Signal Reliability

Signal reliability measures whether a whale-flow signal is decision-useful in the current market regime.

Reliability is different from price-impact risk.

A signal can have extreme price-impact risk but only medium reliability if the flow is large relative to liquidity, but the intent is unclear or the market regime is noisy.

For example:

- a DEX interaction with extreme size ratio and normal volatility may produce a higher-reliability price-impact signal,
- a wallet-to-wallet transfer with extreme size ratio may produce high impact risk but lower reliability because the intent is unclear,
- a DEX interaction during extreme volatility may have high evidence confidence but reduced reliability because price movement may come from broader market stress.

The system should separate:

- **confidence**: how strong the evidence is,
- **risk flag**: what warning should be shown,
- **reliability**: how useful the signal is for interpretation.

### Initial Reliability Framework

| Evidence / Context | Liquidity Condition | Volatility Regime | Signal Reliability |
|---|---|---|---|
| DEX interaction | High or extreme size ratio | Normal | High / Medium-High |
| Exchange inflow | High or extreme size ratio | Normal | Medium-High |
| Exchange outflow | High or extreme size ratio | Normal | Medium |
| Wallet-to-wallet | High or extreme size ratio | Normal | Low-Medium |
| Any flow context | Low size ratio | Normal | Low-Medium / Medium |
| Any flow context | Any size ratio | Extreme | Reduced reliability |
| Unknown context | Any size ratio | Extreme | Low |

These labels are intentionally conservative. The goal is not to overclaim predictive power. The goal is to help the researcher understand whether the whale-flow event is supported by enough context to be useful.

Every reliability label must be paired with a reason.

## Dashboard Output Examples

The dashboard should present whale-flow interpretation as an evidence-backed research view rather than a raw signal.

A useful output should include:

- flow context,
- intent label,
- evidence confidence,
- size ratio,
- liquidity risk,
- volatility regime,
- signal reliability,
- risk flag,
- reason.

### Example 1: Exchange Inflow With High Size Ratio

```text
Flow Context: Exchange Inflow
Intent Label: Possible Sell-Pressure Preparation
Evidence Confidence: Medium
Size Ratio: 18%
Liquidity Risk: Extreme Price-Impact Risk
Volatility Regime: Normal
Signal Reliability: Medium-High
Reason: Whale-flow moved toward an exchange-labeled destination and is large relative to available liquidity. This may indicate sell-pressure preparation, but actual selling is not confirmed.
```

### Example 2: DEX Interaction During Extreme Volatility

```text
Flow Context: DEX Interaction
Intent Label: Protocol-Level Market Action
Evidence Confidence: High
Size Ratio: 22%
Liquidity Risk: Extreme Price-Impact Risk
Volatility Regime: Extreme
Signal Reliability: Medium / Reduced
Reason: DEX interaction evidence is strong and the flow is large relative to liquidity, but extreme volatility may make price movement difficult to attribute only to whale-flow.
```

### Example 3: Wallet-to-Wallet Transfer With Low Size Ratio

```text
Flow Context: Wallet-to-Wallet
Intent Label: Unknown / Possible Internal Movement
Evidence Confidence: Low
Size Ratio: 0.8%
Liquidity Risk: Low Price-Impact Risk / Flow Likely Absorbed
Volatility Regime: Normal
Signal Reliability: Low-Medium
Reason: The flow is small relative to liquidity and the transfer intent is unclear.
```

## Limitations

This mechanism layer is designed to improve interpretation, not to prove intent or predict price perfectly.

Important limitations:

- A whale transfer does not prove buying or selling intent.
- Exchange inflow may indicate possible sell-pressure preparation, but it does not confirm that a sale happened.
- Exchange outflow may indicate withdrawal, custody movement, or possible accumulation, but it does not confirm buying intent.
- Wallet-to-wallet transfers may be internal movements, OTC settlements, custody reshuffles, or unknown activity.
- DEX interaction is stronger evidence than a generic transfer, but it still does not prove the full economic intent.
- Pool depth is a liquidity proxy and may not capture all market liquidity across venues.
- Size-ratio thresholds are initial research heuristics, not universal trading laws.
- Volatile regimes can reduce signal reliability because market movement may come from liquidations, panic, funding unwind, macro shocks, or broader liquidity stress.
- Execution outcomes can be affected by slippage tolerance, block ordering, MEV, and changing pool state.

The system should therefore use cautious language such as:

- possible sell-pressure,
- possible custody movement,
- intent unknown,
- signal may be noisy,
- flow likely absorbed,
- estimated price-impact risk.

It should avoid overconfident language such as:

- whale definitely sold,
- whale definitely bought,
- guaranteed price move,
- guaranteed execution failure.

## Implementation Plan

The first implementation should remain focused and testable.

Proposed modules:

```text
src/analytics/liquidity_risk.py
src/analytics/flow_context.py
```

### Liquidity Risk Module

The liquidity risk module should handle:

- size-ratio calculation,
- price-impact risk classification,
- execution-fragility labels,
- reason generation.

Possible functions:

```text
calculate_size_ratio(whale_flow_usd, pool_depth_usd)
classify_price_impact_risk(size_ratio)
estimate_execution_fragility(size_ratio, assumed_slippage_tolerance_pct)
build_liquidity_risk_reason(...)
```

### Flow Context Module

The flow context module should handle:

- flow-context classification,
- intent-label assignment,
- evidence-confidence assignment,
- reason generation.

Possible functions:

```text
classify_flow_context(...)
infer_intent_label(...)
assign_evidence_confidence(...)
build_flow_context_reason(...)
```

### Testing Requirements

The implementation should include tests for:

- zero or missing pool depth,
- negative values,
- boundary thresholds,
- low / medium / high / extreme size ratios,
- exchange inflow labels,
- exchange outflow labels,
- DEX interaction labels,
- wallet-to-wallet labels,
- unknown flow context,
- reason text generation.

The goal is to keep the system simple, transparent, and defensible before adding more advanced data sources.

## Summary

The Whale-Flow Mechanism Layer upgrades the project from a whale-flow tracker into a more decision-useful research system.

The layer does this by combining:

- whale-flow size,
- liquidity depth,
- flow context,
- evidence confidence,
- volatility regime,
- risk flags,
- signal reliability,
- explainable reasons.

The core principle is:

> Do not treat whale-flow as a standalone signal. Interpret it through liquidity, context, evidence, and regime.

This keeps the project aligned with the goal of building a small but real research system with a clear point of view.


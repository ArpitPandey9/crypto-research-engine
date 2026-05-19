# Whale-Flow Stress Test Note v1

This note explains how I am starting to stress-test the whale-flow signal beyond a basic dashboard.

The goal is not to claim that whale flow predicts price with certainty.

The goal is to ask a more research-grade question:

> Under what market conditions does whale-flow pressure become more useful, less useful, or unreliable?

---

## 1. Why this note exists

The project now includes Ethereum whale-transfer data, Binance ETH/BTC historical price data, DEX Screener pool-depth data, SQLite storage, rolling whale-flow signals, cost-aware backtesting, automatic volatility-regime detection, mechanism signal / liquidity context, dashboard data audit, and full pytest CI.

This note turns the system from “signals on a dashboard” into a more defensible research framework.

---

## 2. Main research question

Can large on-chain whale transfers, when normalized into USD flow pressure and combined with liquidity and volatility context, help identify market-risk conditions?

This is different from saying whale flow always predicts price. The project does not claim that.

---

## 3. Current signal logic

The current signal starts from rolling net whale flow.

- Positive rolling whale flow above threshold means long pressure.
- Negative rolling whale flow below threshold means short pressure.
- Otherwise, the signal stays flat or neutral.

A professional research system must ask when this signal works, when it fails, and when it should be ignored.

---

## 4. Why whale flow may matter

Whale flow may matter because large capital movement can create market pressure.

But a large transfer may represent exchange movement, custody movement, portfolio rebalancing, OTC flow, DeFi liquidity movement, or noise.

So the system should not blindly treat every whale movement as informed flow.

---

## 5. Liquidity absorption risk

Liquidity matters because the same whale flow can have different impact in different market structures.

Simple story:

- Whale flow is the big truck.
- DEX pool depth is the road width.
- Volatility regime is the weather.

If the truck is large and the road is narrow, price-impact risk may be higher. If the road is deep and liquid, the flow may be absorbed more easily.

---

## 6. Volatility regime risk

The same whale-flow signal may behave differently when volatility is normal, high, or extreme.

- Normal volatility: signal may be easier to interpret.
- High volatility: signal may be noisy.
- Extreme volatility: signal may be unreliable or riskier.

This is why the dashboard now uses automatic volatility-regime detection.

---

## 7. Current ETH audit interpretation

The current ETH audit shows that dashboard values are recomputed from SQLite and project formulas, automatic volatility is available, latest rolling whale-flow is zero, and no fake pool-impact signal is generated.

Interpretation:

> When latest whale-flow pressure is zero, the system should not force a mechanism signal.

---

## 8. Current WBTC audit interpretation

The current WBTC audit shows that no WBTC whale-event rows exist in the local database, so the audit stops honestly and does not fabricate strategy numbers.

Interpretation:

> Missing real data should produce an unavailable result, not a fake signal.

---

## 9. Failure modes to test next

Important failure modes:

- no whale-flow pressure
- missing whale-event data
- shallow liquidity
- high volatility
- weak mechanism link
- insufficient data freshness

---

## 10. Decision-useful interpretation

The goal is not just long, short, or flat.

The better research output is:

> signal direction + reliability + liquidity risk + volatility context

Future labels could include:

- signal available
- signal unavailable
- liquidity risk elevated
- volatility regime risky
- mechanism evidence weak
- data unavailable
- research-only, no trade recommendation

---

## 11. What this project does not claim

This project does not claim guaranteed buy signals, guaranteed sell signals, confirmed whale intent, complete market prediction, production trading readiness, or financial advice.

It only studies whale-flow pressure, liquidity absorption risk, and volatility context as research signals.

---

## 12. Next research direction

The next high-value improvement is to make the whale-flow signal more defensible by comparing behavior across volatility regimes, comparing deep versus shallow liquidity conditions, adding reliability labels, and documenting when the signal should be ignored.

Target end state:

> This is not just a dashboard. It is a small but real research system with a clear point of view..
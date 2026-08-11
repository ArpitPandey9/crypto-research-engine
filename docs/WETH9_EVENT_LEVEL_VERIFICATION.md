# WETH9 Large Deposits — Event-Level Verification

## Research question

Do large native-ETH calls to WETH9 represent completed deposits, and what can trailing calldata establish once execution is verified?

The investigation separates **selector evidence** from **execution evidence**. A call beginning with `0xd0e30db0` is consistent with the WETH9 `deposit()` entry point, but the selector alone does not prove that the expected protocol action completed.

[Live Dune dashboard](https://dune.com/arpitpandey/weth9-large-deposits-event-level-verification)

## Fixed research scope

| Field | Scope |
|---|---|
| Network | Ethereum |
| Contract | WETH9 - 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 |
| Research window | 23 Apr 2026 — 22 Jul 2026 |
| Minimum transaction value | 1,000 ETH |
| Target selector | `0xd0e30db0` |
| Target transactions | 135 |
| Unique transaction hashes | 135 |
| Unique sender addresses | 56 |

The fixed-window aggregate is `445941257986580647670085` wei, or **445,941.257987 ETH** after summing exact integer wei and converting once to ETH.

## Verification methodology

Each target transaction passes through the same evidence chain:

```text
large native-ETH transaction
→ WETH9 destination
→ 0xd0e30db0 selector
→ matching WETH9 Deposit event
→ exactly one Deposit event
→ transaction value = event value in exact wei
→ transaction sender = Deposit destination
→ calldata-shape classification
```

This design prevents a function selector from being treated as sufficient proof of protocol execution.

## Verification result

| Control | Result |
|---|---:|
| Matching `Deposit` event | 135 / 135 |
| Exactly one `Deposit` event | 135 / 135 |
| Transaction value = event value, exact wei | 135 / 135 |
| Sender = Deposit destination | 135 / 135 |
| Selector-only calldata | 128 |
| Trailing-calldata transactions | 7 |

All 135 target transactions therefore satisfy the event-level, amount-level, and depositor-level controls used in this investigation.

## Trailing-calldata investigation

Seven verified deposits contain bytes after the four-byte selector. Those seven transactions resolve into three observed byte patterns.

| Observed pattern | Extra bytes | Transactions | Unique senders | Total ETH | Distinct gas-used values | Trailing word = tx value |
|---|---:|---:|---:|---:|---:|---:|
| Repeated 10-byte marker | 10 | 5 | 4 | 7,352 | 1 | 0 |
| 32-byte word = tx value | 32 | 1 | 1 | 1,004 | 1 | 1 |
| Single-byte marker | 1 | 1 | 1 | 3,600 | 1 | 0 |

Observed trailing bytes:

- repeated 10-byte marker: `0x756e697800000000000c`
- 32-byte word: `0x0000000000000000000000000000000000000000000000366d4c88947c300000`
- single-byte marker: `0x76`

The five repeated-marker transactions share the same trailing bytes and the same observed gas usage (`45138`). That is evidence of execution-shape consistency only; it is not entity, wallet, relayer, or infrastructure attribution.

For one transaction, the 32-byte trailing word numerically equals the transaction value (`1004000000000000000000` wei). WETH9 `deposit()` has no ABI argument, so this equality is recorded as an observed calldata property rather than interpreted as an encoded deposit-amount parameter.

## Evidence boundary

### Established

- all seven trailing-calldata cases are successful, event-verified WETH9 deposits under the controls above;
- the seven cases group into three observed byte patterns with counts `5 / 1 / 1`;
- the repeated 10-byte marker occurs across four sender addresses;
- one 32-byte trailing word numerically equals its transaction value.

### Not established

The evidence does **not** establish:

- semantic meaning of the extra bytes;
- wallet or client software;
- common entity ownership;
- relayer or exchange attribution;
- shared infrastructure;
- economic intent.

A sender address is an on-chain address, not proof of a unique person or organization.

## Query lineage

### Canonical evidence queries

| Query | Role |
|---|---|
| [8077635 — Verification Summary](https://dune.com/queries/8077635) | Fixed-window totals and verification controls |
| [8078688 — Trailing-Calldata Review](https://dune.com/queries/8078688) | Transaction-level evidence for all seven exceptions |
| [8078757 — Pattern Summary](https://dune.com/queries/8078757) | Canonical grouping into three observed patterns |

### Presentation queries

| Query | Role |
|---|---|
| [8279596 — Dashboard Headline Metrics](https://dune.com/queries/8279596) | Headline counters |
| [8279907 — Verification Coverage](https://dune.com/queries/8279907) | Verification-control visualization |
| [8280175 — Calldata Shape Split](https://dune.com/queries/8280175) | Selector-only vs trailing-calldata split |
| [8287056 — Pattern Display Labels](https://dune.com/queries/8287056) | Human-readable labels for the final pattern chart and table |

Presentation queries reuse canonical outputs for display. They do not redefine the underlying verification or pattern-classification logic.

## Reproducibility

Before publication, the three fixed-window canonical queries were freshly re-executed.

- `8077635` reproduced the fixed-window verification totals.
- `8078757` reproduced the three canonical pattern rows.
- `8078688` reproduced the same seven transaction identities and substantive evidence fields. The only observed difference versus the frozen local export was serialization of a missing value (`<nil>` versus an empty field), not transaction or evidence drift.

The public repository does not include Dune API credentials, local dashboard backups, raw audit archives, or private operational files. Reproduction should start from the public canonical Dune queries above and the fixed research scope documented here.

## Interpretation

The primary result is methodological: **selector evidence and verified execution should not be conflated**.

In this fixed sample, every target call passed independent event, amount, and depositor checks. The trailing-calldata subset then supported a narrow forensic observation—three repeatable byte shapes—while the analysis stopped short of unsupported semantic or entity attribution.

That boundary between what the chain proves and what it merely suggests is the main research output of this case study.

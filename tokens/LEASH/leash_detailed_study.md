# Detailed Study of LEASH (Doge Killer)

**Analysis date**: 2026-08-31
**Contract**: [`0x27C70Cd1946795B66be9d954418546998b546634`](https://etherscan.io/address/0x27C70Cd1946795B66be9d954418546998b546634) (Ethereum Mainnet)
**Contract name**: `UFragments` — an Ampleforth-derived elastic supply token

---

## Executive Summary

LEASH is not a fixed-supply ERC20. It is a **rebase token**: balances are held
internally in a hidden denomination ("gons") and the public supply is rescaled
by an automated monetary policy. Every holder's balance moves with each rebase,
proportionally.

Between 2025-08-11 and 2026-06-25 the contract executed **311 consecutive
expansionary rebases**, roughly +10% each, growing the supply from 118,411
tokens to **803,760,032,105,055,232**. Measured from the 2020 floor of
107,646.85, that is a factor of about **7.5 trillion**.

The expansion has stopped, but not by decision: the price oracle feeding the
policy has expired and now returns `(0, false)`, and the policy contains
`require(rateValid)`. Every rebase attempt currently reverts.

The critical finding is what happens next. Ownership is renounced on the token,
the policy **and** the orchestrator, so `setRebasePaused`, `setMonetaryPolicy`
and `setTokenPaused` are permanently unreachable. The one contract in the chain
that still has a live owner is the **oracle** — and its owner can register a new
price provider. **One party can restart the expansion; nobody can stop it.**

Rebases are proportional, so no holder is diluted relative to another. The harm
is not economic dilution — it is that every off-chain representation of this
token is wrong, and that a supply-critical control sits with a single key while
every corrective control has been destroyed.

### Severity Breakdown

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 2 |
| Medium | 2 |
| Low | 1 |
| Informational | 2 |

### Key Recommendations

Note that **none of these can be applied to the deployed system** — renounced
ownership makes them permanently impossible. They are stated for anyone
deploying a comparable design.

1. **Never renounce ownership of a contract that retains an active control
   path.** Renouncement here destroyed the emergency brake while leaving the
   engine running.
2. **Make the safety control at least as durable as the power it restrains.**
   `setRebasePaused` should not be reachable only by an owner that the design
   expects to disappear.
3. **Bound the oracle's authority.** A single provider with a 24-hour report
   window drives unbounded supply changes with no sanity band and no circuit
   breaker.

---

## 1. Contract Overview

| Field | Value |
|---|---|
| Token name | DOGE KILLER (LEASH) |
| Contract name | `UFragments` |
| Compiler | `0.4.24+commit.e67f0147` |
| Decimals | 18 |
| Initial supply | 122,222.22 (`12222222 * 10**(DECIMALS-2)`) |
| Supply cap | `MAX_SUPPLY = 2**128 - 1` ≈ 340,282,366,920,938,487,808 tokens |
| Current supply | **803,760,032,105,055,232** |
| Verified | Yes |
| Proxy | No |
| Deployer | `0xA221af4a429b734Abb1CC53Fbd0c1D0Fa47e1494` |

### The gon denomination

```solidity
uint256 private constant INITIAL_FRAGMENTS_SUPPLY = 12222222 * 10**(DECIMALS - 2);
uint256 private constant TOTAL_GONS = MAX_UINT256 - (MAX_UINT256 % INITIAL_FRAGMENTS_SUPPLY);
uint256 private constant MAX_SUPPLY = ~uint128(0);
```

`TOTAL_GONS` is fixed forever. A rebase changes only `_gonsPerFragment`, the
conversion rate between the internal unit and the displayed balance:

```solidity
_gonsPerFragment = TOTAL_GONS.div(_totalSupply);
```

Because every balance is stored in gons and converted on read, all balances
scale together. **Relative ownership is unchanged by a rebase** — this is the
property that keeps the findings below out of the Critical band.

---

## 2. The Rebase History

315 `LogRebase` events, in two entirely separate episodes.

### Episode one — September 2020, contraction

| Epoch | Block | Resulting supply |
|---|---|---|
| 1 | 10,822,663 | 125,218.57 |
| 2 | 10,829,179 | 119,434.38 |
| 3 | 10,835,810 | 114,116.76 |
| 4 | 10,842,239 | **107,646.85** |

Four rebases across three days, all contractionary — the mechanism behaving as
designed.

**That last figure deserves attention: 107,646.85 is the supply that market data
providers still report for LEASH today.** They are anchored to block 10,842,239,
2020-09-11.

### The dormancy

**12,277,495 blocks** — very nearly five years — with no rebase at all.

### Episode two — August 2025 to June 2026, expansion

311 consecutive expansionary rebases, one per day, each approximately +10%:

| Epoch | Block | Resulting supply |
|---|---|---|
| 5 | 23,119,734 | 118,411.53 |
| 50 | 23,491,926 | 8,631,073.99 |
| 100 | 23,849,199 | 1,013,209,137.07 |
| 150 | 24,206,124 | 118,941,484,745.60 |
| 200 | 24,571,599 | 13,962,642,337,062.91 |
| 250 | 24,930,124 | 1,639,086,492,401,956.75 |
| 315 | 25,396,467 | **803,760,032,105,055,232.00** |

Not one contraction in 311 rebases. A functioning feedback loop should
oscillate around its target; this one expanded monotonically for ten months.

**Why that matters mechanically.** The policy computes:

```solidity
supplyDelta = totalSupply * (rate - targetRate) / targetRate;
supplyDelta = supplyDelta.div(rebaseLag);   // rebaseLag = 10
```

A +10% supply change per rebase, damped by a factor of 10, implies the oracle
reported a rate roughly **double** the target — every single day, for 311 days,
while the supply grew by twelve orders of magnitude. A price feed tracking a
real market could not behave that way. The reported rate was not responding to
the supply it was driving.

### Current state

| Reading | Value |
|---|---|
| `marketOracle.getData()` | **`(0, false)`** — no valid data |
| Policy behaviour | `require(rateValid)` → **every rebase reverts** |
| `rebasePaused` | `false` — the pause was never engaged |
| Last rebase | block 25,396,467 (2026-06-25) |
| Headroom to `MAX_SUPPLY` | **423×**, about **63 further +10% rebases** |

The expansion did not stop because anyone stopped it. It stopped because the
oracle's reports expired — `reportExpirationTimeSec` is 86,400 seconds, and
nobody has published since.

---

## 3. Control Chain

This is the heart of the analysis.

| Contract | Address | Owner | Consequence |
|---|---|---|---|
| `UFragments` (token) | `0x27C70Cd1…b546634` | **`0x0` — renounced** | `setRebasePaused`, `setMonetaryPolicy`, `setTokenPaused` permanently unreachable |
| `UFragmentsPolicy` | `0xEff020b0…e6636B` | **`0x0` — renounced** | policy parameters frozen |
| `Orchestrator` | `0xCaf4aa3A…936C658` | **`0x0` — renounced** | frozen |
| `MedianOracle` | `0x8a920C85…4A3eeDcB` | **`0x01e0C58E…9DC5c50b` — LIVE** | **can register price providers** |

Three of the four are frozen. The fourth is not.

The oracle owner holds `addProvider`, `removeProvider`, `setMinimumProviders`,
`setReportExpirationTimeSec` and `setTargetAsset`. With `minimumProviders` set
to 1 and exactly one provider currently registered, **adding a provider that
reports a rate above target is sufficient to restart the expansion**.

That owner, `0x01e0C58EebE0e8B8435458B191a9bb049DC5c50b`, is an EOA carrying an
**EIP-7702 delegation** (`EIP7702StatelessDeleGator`, a MetaMask smart-account
implementation). Explorers label it a contract; it is a single-key account.

**The asymmetry is the finding.** Renouncing ownership is widely treated as a
decentralisation milestone. Here it removed every corrective control — the
pause, the policy swap, the token freeze — while leaving the supply-driving
control intact behind one private key. The system cannot be stopped, only
restarted.

---

## 4. Findings Register

| ID | Finding | Severity |
|---|---|---|
| H-01 | Supply expansion can be restarted by a single key and stopped by no one | High |
| H-02 | Renounced ownership destroyed every emergency control | High |
| M-01 | Supply grew ~7.5 trillion× with no bound, sanity band or circuit breaker | Medium |
| M-02 | Single-provider oracle drives unbounded supply changes | Medium |
| L-01 | Published market data understates supply by ~12 orders of magnitude | Low |
| I-01 | `MAX_SUPPLY` reachable in roughly 63 further rebases | Informational |
| I-02 | Legacy compiler (0.4.24) with no upgrade path | Informational |

---

### H-01 — Expansion is restartable by one key, stoppable by none · High

**Description.** `rebase()` is gated by `onlyMonetaryPolicy`. The policy accepts
a rate from `MedianOracle`, whose owner may register providers at will. With
`minimumProviders = 1`, one new provider reporting above target resumes
expansion at the next daily window.

No counterparty exists. `setRebasePaused` is `onlyOwner` on a token whose owner
is `0x0`; `setMonetaryPolicy` likewise. There is no timelock, no governance, no
multisig, and no path to add one.

**Impact.** Supply can be driven upward indefinitely — bounded only by
`MAX_SUPPLY`, roughly 63 rebases away — at the discretion of one key holder,
irreversibly.

Holders are not diluted relative to one another, which is what keeps this below
Critical. The damage is to every integration that assumes a stable supply, to
price and market-cap representations, and to any contract holding LEASH whose
accounting assumes fixed balances.

**Recommendation.** Not applicable to the deployed system — no control path
remains. For comparable designs: never renounce ownership while an active
control path survives elsewhere in the chain.

---

### H-02 — Renouncement destroyed the emergency controls · High

**Description.** The token exposes `setRebasePaused(bool)` — a purpose-built
circuit breaker for exactly the situation the contract is now in. It is
`onlyOwner`, and the owner is `0x0`.

`rebasePaused` currently reads `false`. The brake exists, is disengaged, and can
never be applied.

**Impact.** The one mechanism the authors provided against runaway rebasing was
permanently disabled by an action generally presented as a safety improvement.
The same applies to `setMonetaryPolicy` — a broken policy cannot be replaced —
and `setTokenPaused`.

**Recommendation.** Safety controls should outlive ownership renouncement, or
renouncement should be blocked while such controls remain necessary. A design
that can be renounced into an unstoppable state is under-specified.

---

### M-01 — Unbounded expansion with no sanity constraints · Medium

**Description.** The policy applies whatever the oracle reports, damped by
`rebaseLag = 10` and clamped only at `MAX_SUPPLY`. There is no maximum
per-rebase change, no deviation band against the previous rate, no staleness
guard beyond report expiry, and no cumulative limit.

**Impact.** 311 consecutive expansions produced a ~7.5 trillion× supply increase
before the oracle happened to expire. Nothing in the contract objected — the
outcome was within its rules.

**Recommendation.** Cap per-rebase change; reject rates deviating implausibly
from the previous accepted value; require a minimum provider count above one.

---

### M-02 — Single-provider oracle · Medium

**Description.** `minimumProviders = 1` with one provider registered. A
`MedianOracle` with a single provider computes the median of one value.

**Impact.** Every rebase in episode two rested on one reporting source, with no
cross-check. The evidence suggests that source was not tracking a real market:
a genuine price feed would not report roughly twice target for 311 consecutive
days while supply grew twelve orders of magnitude.

**Recommendation.** Require at least three independent providers.

---

### L-01 — Published supply data is stale by five years · Low

**Description.** Market data providers report LEASH supply as ~107,646 tokens —
the value set at epoch 4 on 2020-09-11. The on-chain value is
803,760,032,105,055,232.

**Impact.** Every derived figure is wrong by roughly twelve orders of magnitude:
market capitalisation, fully-diluted valuation, share-of-supply for any holder,
and any position sizing based on them. This is not a contract defect, but it is
a direct consequence of the contract's design meeting infrastructure that
assumes fixed supply.

**Reproduction.**

```bash
cast call 0x27C70Cd1946795B66be9d954418546998b546634 \
  "totalSupply()(uint256)" --rpc-url https://ethereum-rpc.publicnode.com
# 803760032105055242245609937123889209  (÷1e18 for tokens)
```

The repository tool flags this automatically:

```bash
python3 tools/onchain_profile.py 0x27C70Cd1946795B66be9d954418546998b546634
# IDENTITY → total supply: 803,760,032,105,055,232   << ELASTIC
# SUPPLY MECHANICS — ELASTIC → 315 rebase events, 6.4 trillion× growth
```

---

### I-01 — Supply ceiling within reach · Informational

`MAX_SUPPLY` is `2**128 - 1`. Current supply sits at 1/423 of it — about **63
further +10% rebases**, roughly two months at the previous daily cadence. On
reaching it the contract clamps:

```solidity
if (_totalSupply > MAX_SUPPLY) { _totalSupply = MAX_SUPPLY; }
```

Behaviour at the ceiling is defined and safe, but the token would be pinned
there permanently, with `_gonsPerFragment` at its minimum and rounding
truncation at its most severe.

---

### I-02 — Legacy compiler, no upgrade path · Informational

Compiled with `0.4.24` (2018). Not upgradeable, and — with ownership renounced —
not replaceable. Notably the contract predates Solidity 0.8's built-in overflow
checks and relies on `SafeMath`/`SafeMathInt`, which is correct for its era.

---

## 5. Verification Status

| Check | Result |
|---|---|
| Source verified on explorers | Yes |
| Repository copy matches on-chain source | Yes — retrieved from the verified source |
| Compiler | `0.4.24+commit.e67f0147` |
| Proxy / upgradeable | No |
| Ownership | Renounced (token, policy, orchestrator); **live on oracle** |
| Rebase mechanism | Active by design, currently blocked by expired oracle |
| Test suite in repository | None |

---

## 6. Reproducing These Findings

```bash
L=0x27C70Cd1946795B66be9d954418546998b546634
POLICY=0xEff020b07a292baad7A948897c87F99e4Fe6636B
ORACLE=0x8a920C8565783c3aE4aA236e92A5227c4A3eeDcB
R=https://ethereum-rpc.publicnode.com

# Current supply, and the fact that nobody owns the token
cast call $L "totalSupply()(uint256)" --rpc-url $R
cast call $L "owner()(address)"       --rpc-url $R   # 0x0
cast call $L "rebasePaused()(bool)"   --rpc-url $R   # false — brake never applied

# The full rebase history (315 events)
curl -s -A "Mozilla/5.0" "https://eth.blockscout.com/api?module=logs&action=getLogs\
&fromBlock=0&toBlock=latest&address=$L\
&topic0=0x72725a3b1e5bd622d6bcd1339bb31279c351abe8f541ac7fd320f24e1b1641f2"

# Why rebases currently revert
cast call $ORACLE "getData()(uint256,bool)" --rpc-url $R   # (0, false)

# The control chain: three renounced, one live
cast call $POLICY "owner()(address)"          --rpc-url $R   # 0x0
cast call $POLICY "orchestrator()(address)"   --rpc-url $R
cast call $ORACLE "owner()(address)"          --rpc-url $R   # LIVE
cast call $ORACLE "minimumProviders()(uint256)" --rpc-url $R # 1

# Full profile with automatic elastic-supply detection
python3 tools/onchain_profile.py $L
```

---

## Disclaimer

Educational analysis based on public blockchain data and verified source code.
Not affiliated with the Shiba Inu ecosystem or any project named. Not a formal
audit. Sections 1–3, 5 and the reproduction commands state verifiable facts;
section 4 severities are analytical judgements calibrated to this repository's
scale. Chain state is current as of the analysis date and rebases may resume.
Nothing here is financial, investment or legal advice.

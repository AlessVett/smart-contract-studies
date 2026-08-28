# Detailed Study of Rexas_Presale

**Analysis date**: 2026-08-28
**Contract**: [`0xa9502665b39b0e61F2CbbFfAD139688615fB16F6`](https://etherscan.io/address/0xa9502665b39b0e61F2CbbFfAD139688615fB16F6) (Ethereum Mainnet)
**Related study**: [`tokens/RXS/`](../../tokens/RXS/) — the token this contract sold

---

## Executive Summary

`Rexas_Presale` is a multi-stage token sale contract that accepted ETH, USDT and
USDC, priced in USD through a Chainlink feed, and delivered tokens to the buyer
in the same transaction as payment. It processed **109,189 purchases from 53,910
unique buyers, recording $55,999,997.01 raised** across 12 stages.

The accounting is sound and the transaction paths are well constructed: purchases
are `nonReentrant`, state is updated before external calls, hardcaps are enforced,
and the raise counter cannot be inflated by any administrative function. Funds are
never held by the contract — each payment is forwarded to a collection wallet at
purchase time.

The risk is concentrated almost entirely in **owner privilege**. The owner can
replace the price oracle, change which token is sold, redirect the stablecoin
addresses, and blacklist buyers — with no timelock, no events, and a single EOA
key. None of these powers were abused: on-chain history shows the owner only ever
called stage-management and `changeFundWallet`.

### Severity Breakdown

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 1 |
| Medium | 4 |
| Low | 2 |
| Informational | 2 |

### Key Recommendations

1. **Remove `ChangeOracleAddress`, or place it behind a timelock.** An arbitrary
   oracle gives the owner unilateral control over the ETH→token exchange rate.
2. **Validate the Chainlink response.** `getLatestPrice()` accepts whatever the
   feed returns, including stale rounds and non-positive answers.
3. **Emit events on administrative changes.** Oracle, sale token, stablecoin
   addresses and blacklist all change silently.
4. **Use `SafeERC20` in `WithdrawTokens`.** As written it cannot recover USDT —
   see L-01, which has already materialised.

---

## 1. Contract Overview

| Field | Value |
|---|---|
| Contract name | `Rexas_Presale` |
| Compiler | `0.8.26+commit.8a97fa7a` |
| Optimizer | **Disabled** |
| License | None declared |
| Source lines | 783 |
| Verified | Yes |
| Proxy | No — bytecode immutable |
| Deployer / owner | `0xf6Be37a90E6c996A6f75f58067cB845c0c8d343d` (EOA) |

### Deployed configuration (live)

| Parameter | Value |
|---|---|
| `SaleToken` | `0x9eAeBd7E…550e224c` (RXS) — never changed |
| `USDTInterface` | `0xdAC17F95…3D831ec7` (canonical USDT) — never changed |
| `USDCInterface` | `0xA0b86991…3606eB48` (canonical USDC) — never changed |
| `fundReceiver` | `0x6516c79E…08bF6737` — changed 3 times |
| `currentSale` | 12 |
| `MinTokenTobuy` | 1 |
| `getLatestPrice()` | returns ~$2,477 per ETH, consistent with market |

---

## 2. Architecture

```
ReentrancyGuard ─┐
                 ├── Rexas_Presale
Ownable ─────────┘
   └── Context

Dependencies: IERC20, IERC20Metadata, Aggregator (Chainlink), Address library
```

The `Aggregator` interface exposes only `latestRoundData()`. The contract holds
it as `Aggregator internal aggregatorInterface` — not public, so the configured
oracle address cannot be read through a getter.

### Core data structure

```solidity
struct PresaleData {
    uint256 startTime;
    uint256 endTime;
    uint256 price;
    uint256 nextStagePrice;
    uint256 Sold;
    uint256 tokensToSell;
    uint256 UsdtHardcap;
    uint256 amountRaised;
    bool Active;
}
```

`price` is expressed as **tokens per USD**, not USD per token: stage 1 stores
`33.3333`, which corresponds to $0.03 per token.

---

## 3. Purchase Path

All three entry points share the same shape. `buyWithEth()`:

```solidity
uint256 usdAmount = (msg.value * getLatestPrice() * USDT_MULTIPLIER) /
    (ETH_MULTIPLIER * ETH_MULTIPLIER);
require(presale[currentSale].amountRaised + usdAmount <= presale[currentSale].UsdtHardcap, ...);
require(!isBlackList[msg.sender], ...);
require(!paused[currentSale], ...);
...
presale[currentSale].Sold += tokens;
presale[currentSale].amountRaised += usdAmount;
overalllRaised += usdAmount;
userData[_msgSender()][currentSale].investedAmount += usdAmount;
...
sendValue(payable(fundReceiver), msg.value);
bool status = IERC20(SaleToken).transfer(_msgSender(), tokens);
require(status, "Token transfer failed");
```

**What is done correctly here**, and is worth stating explicitly because it is
often absent in sale contracts of this kind:

- `nonReentrant` on all three buy functions
- **checks-effects-interactions respected** — every state variable is updated
  before `sendValue` and before the token transfer
- the token transfer's return value **is** checked (`require(status, …)`)
- hardcap enforced per stage, and `checkSaleState` bounds the amount against
  `tokensToSell - Sold`
- `sendValue` uses `.call{value:}` rather than `.transfer()`, so it is not
  exposed to the 2300 gas stipend problem

Funds are forwarded immediately; the contract is never a custodian.

---

## 4. Findings Register

| ID | Finding | Severity |
|---|---|---|
| H-01 | Owner can substitute the price oracle with an arbitrary contract | High |
| M-01 | `getLatestPrice()` performs no validation of the Chainlink response | Medium |
| M-02 | Owner can change the sale token after buyers have paid | Medium |
| M-03 | Owner can redirect the USDT/USDC addresses | Medium |
| M-04 | Owner is a single EOA with no timelock | Medium |
| L-01 | `WithdrawTokens` cannot recover non-compliant tokens | Low |
| L-02 | Owner can blacklist arbitrary buyers | Low |
| I-01 | No events on critical administrative changes | Informational |
| I-02 | Optimizer disabled; no licence declared | Informational |

---

### H-01 — Arbitrary oracle substitution · High

**Description.**

```solidity
function ChangeOracleAddress(address _oracle) public onlyOwner {
    aggregatorInterface = Aggregator(_oracle);
}
```

Any address can be installed as the price feed. The only interface requirement is
a `latestRoundData()` returning a five-tuple.

**Impact.** `getLatestPrice()` is the sole determinant of how much RXS a buyer
receives for a given amount of ETH. With a controlled oracle the owner sets that
rate freely: a deflated price makes ETH buyers receive proportionally fewer
tokens for the same payment, a direct loss to them. There is no timelock, no
event, and no bound on the deviation, so a substitution takes effect in the very
next block and is invisible to anyone not monitoring storage.

Stablecoin purchases are unaffected — `buyWithUSDT`/`buyWithUSDC` do not consult
the oracle.

**Status on the deployed contract.** `ChangeOracleAddress` has **never been
called**. Transaction history for the owner shows only `createPresale` (12×),
`setPresaleStage` (12×), `updatePresale` (6×) and `changeFundWallet` (3×). The
live feed returns a value consistent with market ETH/USD.

**Recommendation.** Remove the setter, or gate it behind a timelock with an
emitted event and a sanity band against the previous price.

---

### M-01 — Unvalidated oracle response · Medium

**Description.**

```solidity
function getLatestPrice() public view returns (uint256) {
    (, int256 price, , , ) = aggregatorInterface.latestRoundData();
    price = (price * (10**10));
    return uint256(price);
}
```

Three of the five returned fields are discarded. Absent are:

- a **staleness check** — `updatedAt` is ignored, so a feed that stops updating
  keeps pricing sales at its last value indefinitely
- a **positivity check** — `price` is `int256` and cast to `uint256` without
  testing `> 0`; a negative answer becomes an enormous unsigned number
- a **round completeness check** — `answeredInRound` and `roundId` are discarded

**Impact.** A stale feed is the realistic case and produces silent mispricing in
whichever direction the market has moved: buyers either overpay or acquire
tokens below the intended stage price, with no revert to signal it.

A negative or zero answer degrades to denial of service rather than theft: the
inflated `usdAmount` fails the hardcap `require`, and `checkSaleState` rejects
the resulting token amount. The failure mode is accidental rather than designed,
but it does bound the damage.

**Recommendation.**

```solidity
(uint80 roundId, int256 price, , uint256 updatedAt, uint80 answeredInRound) =
    aggregatorInterface.latestRoundData();
require(price > 0, "Invalid price");
require(updatedAt != 0 && block.timestamp - updatedAt <= MAX_AGE, "Stale price");
require(answeredInRound >= roundId, "Incomplete round");
```

---

### M-02 — Sale token can be changed mid-sale · Medium

**Description.** `ChangeSaleToken(address _token)` reassigns `SaleToken` with no
restriction.

**Impact.** Buyers after the change receive a different asset than the one
advertised, in the same transaction as their payment, with no on-chain warning.
The change is not retroactive — tokens already delivered are unaffected, since
delivery is immediate — which is what keeps this below High.

A secondary effect: the accounting in `usdToTokens` reads
`IERC20Metadata(SaleToken).decimals()` in `ethBuyHelper`, so a replacement token
with different decimals silently changes quoted amounts.

**Status.** Never called; `SaleToken` still returns the RXS address.

**Recommendation.** Freeze the sale token after the first stage is created, or
require that no active presale exists when changing it.

---

### M-03 — Stablecoin addresses are mutable · Medium

**Description.** `changeUSDTToken` and `changeUSDCToken` reassign the payment
token addresses.

**Impact.** `buyWithUSDT` calls `transferFrom` on whatever address is configured.
A buyer who has granted an allowance to the contract for a *previous* address is
not directly at risk from a swap, since the allowance is per-token. The realistic
exposure is a redirect to a worthless token that an attacker-controlled owner
also holds an allowance for, or simple disruption of the payment path.

**Status.** Both still return the canonical mainnet addresses.

**Recommendation.** Make both immutable, set at construction.

---

### M-04 — Single-key ownership, no timelock · Medium

**Description.** Owner is `0xf6Be37a90E…8d343d`, an EOA. Every finding above is
gated only by that key.

**Impact.** Compromise of one private key grants the full privilege set: oracle
substitution (H-01), sale token change (M-02), stablecoin redirection (M-03),
blacklisting (L-02), plus `WithdrawTokens` and `WithdrawContractFunds`. Since the
contract does not custody funds, the loss ceiling is bounded by in-flight
purchases and whatever assets sit in the contract, not by the $56M raised.

**Note on attribution.** The presale deployer and the RXS token deployer are
distinct addresses, but both were funded from Binance hot wallets on 2024-08-28,
fourteen minutes apart, in near-identical amounts. See
[`tokens/RXS/rxs_onchain_analysis.md`](../../tokens/RXS/rxs_onchain_analysis.md) §3.

**Recommendation.** Migrate to a multisig.

---

### L-01 — `WithdrawTokens` cannot recover non-compliant tokens · Low

**Description.**

```solidity
function WithdrawTokens(address _token, uint256 amount) external onlyOwner {
    IERC20(_token).transfer(fundReceiver, amount);
}
```

Two defects in one line: the call goes through an interface declaring
`returns (bool)`, which reverts against tokens returning no data (USDT); and the
return value is **not checked**, so a token returning `false` instead of
reverting would fail silently.

Note the inconsistency with the purchase path, which does check
`require(status, "Token transfer failed")`.

**Impact.** USDT sent to this contract is permanently unrecoverable. Already
materialised: the contract holds **46.85 USDT** that nobody can withdraw. The
14.00 USDC it also holds *is* recoverable, USDC being compliant.

**Proof of concept.** Simulated against mainnet state from the owner address:

```bash
P=0xa9502665b39b0e61F2CbbFfAD139688615fB16F6
OWNER=0xf6Be37a90E6c996A6f75f58067cB845c0c8d343d
R=https://ethereum-rpc.publicnode.com

cast call $P "WithdrawTokens(address,uint256)" \
  0xdAC17F958D2ee523a2206206994597C13D831ec7 1000000 --from $OWNER --rpc-url $R
# → execution reverted

cast call $P "WithdrawTokens(address,uint256)" \
  0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 1000000 --from $OWNER --rpc-url $R
# → 0x  (success)
```

Or with the repository tool, which reports it automatically:

```bash
python3 tools/onchain_profile.py 0xa9502665b39b0e61F2CbbFfAD139688615fB16F6
```

**This is the second instance of the same defect from the same team** — the RXS
token contract has the identical bug in `removeStuckToken`, with 2,320.36 USDT
stuck. See [`tokens/RXS/rxs_detailed_study.md`](../../tokens/RXS/rxs_detailed_study.md)
finding L-01.

**Recommendation.** `SafeERC20.safeTransfer`.

---

### L-02 — Arbitrary buyer blacklisting · Low

**Description.** `blackListUser(address, bool)` sets a flag checked by all three
buy functions.

**Impact.** The owner can exclude any address from participating, without
criteria, notice or event. It cannot seize or freeze tokens already delivered —
delivery is immediate and the token contract has no blacklist — so the impact is
limited to access, not property.

**Recommendation.** Emit an event; document the policy under which it is used.

---

### I-01 — No events on administrative changes · Informational

The contract defines events for `PresaleCreated`, `PresaleUpdated`,
`TokensBought`, `TokensClaimed`, `PresalePaused` and `PresaleUnpaused` — but
**not** for `ChangeOracleAddress`, `ChangeSaleToken`, `changeUSDTToken`,
`changeUSDCToken`, `changeFundWallet`, `blackListUser` or `ChangeMinTokenToBuy`.

The changes that most affect buyers are precisely the ones that leave no log.
`changeFundWallet` was in fact called three times during the sale; reconstructing
that required decoding transaction input, since no event records it.

---

### I-02 — Build configuration · Informational

Optimizer disabled, and no SPDX licence declared. The first raises deployment and
per-transaction gas for a contract that processed 109,189 purchases; the second
leaves reuse terms unstated for a contract published as verified source.

---

## 5. On-Chain Behaviour

Measured, not asserted. Full derivation in
[`tokens/RXS/rxs_onchain_analysis.md`](../../tokens/RXS/rxs_onchain_analysis.md) §5–6.

| Metric | Value |
|---|---|
| `overalllRaised` | 55,999,997.01 USD |
| `uniqueBuyers` | 53,910 |
| Purchase transactions | 109,189 |
| Stages | 12, priced $0.03 → $0.20 |
| Tokens sold | 499,997,696 of 500,000,000 (99.9995%) |
| Collection wallets | 3, rotated via `changeFundWallet`; all now drained |
| USDC purchases | **zero** — the channel was never used |

The per-stage sum of `amountRaised` matches `overalllRaised` to the cent, which
cross-validates the accounting. No administrative function can increment
`overalllRaised`: it is written only inside the three buy functions.

---

## 6. Verification Status

| Check | Result |
|---|---|
| Source verified on explorers | Yes |
| Repository copy matches on-chain source | Yes — retrieved directly from the verified source |
| Compiler | `0.8.26+commit.8a97fa7a`, optimizer disabled |
| Proxy / upgradeable | No |
| Test suite in repository | None |
| Audit | None found covering this contract — the CertiK audit referenced by the project covers the ERC20 token only |

The last row is worth emphasising: the contract that handled **$56 million** is,
as far as public records show, **unaudited**. The audit the project advertises
examined the token, which never custodied anything.

---

## 7. Reproducing These Findings

```bash
P=0xa9502665b39b0e61F2CbbFfAD139688615fB16F6
R=https://ethereum-rpc.publicnode.com

# Raise accounting
cast call $P "overalllRaised()(uint256)" --rpc-url $R   # ÷1e6 = USD
cast call $P "uniqueBuyers()(uint256)"   --rpc-url $R
cast call $P "presale(uint256)" 12       --rpc-url $R

# Owner-controlled configuration
cast call $P "SaleToken()(address)"      --rpc-url $R
cast call $P "USDTInterface()(address)"  --rpc-url $R
cast call $P "fundReceiver()(address)"   --rpc-url $R
cast call $P "getLatestPrice()(uint256)" --rpc-url $R   # ÷1e18 = USD per ETH

# Which admin functions were ever called
curl -s "https://eth.blockscout.com/api/v2/addresses/0xf6Be37a90E6c996A6f75f58067cB845c0c8d343d/transactions?filter=from"

# Full profile, including the L-01 probe
python3 tools/onchain_profile.py $P
```

Note that `aggregatorInterface` is `internal`, so the configured oracle address
cannot be read through a getter; `getLatestPrice()` is the observable proxy for
whether it is behaving.

---

## Disclaimer

Educational analysis based on public blockchain data and verified source code.
Not affiliated with Rexas Finance or any exchange named. Not a formal audit.
Sections 1–3, 5 and 6 state verifiable facts; section 4 severities are analytical
judgements calibrated to this repository's scale. Chain state is current as of
the analysis date. Nothing here is financial, investment or legal advice.

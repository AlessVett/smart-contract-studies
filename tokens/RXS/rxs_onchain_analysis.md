# RXS On-Chain Analysis

**Analysis date**: 2026-08-28
**Contract**: `0x9eAeBd7E73D97E78c77fAB743e6FFA1b550e224c` (Ethereum Mainnet)
**Companion document**: [`rxs_detailed_study.md`](./rxs_detailed_study.md)

> **Relationship to the existing study.** The companion document analyses what the source code *can* do. This document records what *actually happened* on-chain: who holds ownership, how the supply was allocated, how much capital was raised, where it went, and how the market behaved after launch. No finding in the original study is removed or superseded; corrections to specific data points are listed in section 14 with their date.

---

## 1. Scope and Methodology

All technical claims below were obtained from public blockchain data and are reproducible without API keys (see section 13).

| Source | Use |
|---|---|
| `eth_call` via public RPC | live contract state (`owner`, balances, presale counters) |
| `eth_getLogs` | ownership transfer history |
| Blockscout API v1/v2 | transaction history, token transfers, address metadata |
| Verified source code | access-control and accounting review |
| Foundry `cast` | typed contract reads |

**Two limitations are stated up front and repeated in context:**

1. Explorer endpoints truncate at 10,000 records. Of the 109,189 presale purchase transactions, roughly 22,000 were reconstructed. Aggregate ETH and USDT figures in section 6 are therefore **lower bounds, not totals**.
2. Order-book depth on centralised exchanges is not observable on-chain. Section 9 measures the decentralised pool only.

---

## 2. Ownership Status

Live read of `owner()` (selector `0x8da5cb5b`):

```
0x00000000000000000000000048ee57b01d226d1e1efae1fb15f45d9a11bd018a
```

**Owner: `0x48Ee57b01D226d1E1efAE1Fb15f45D9A11Bd018A`**

| Property | Value |
|---|---|
| Account type | **EOA** — single private key, not a multisig or timelock |
| Same as deployer | Yes — creation tx `0x496ab249…ea2ac5`, block 20700162, 2024-09-07 17:17:11 UTC |
| `OwnershipTransferred` events since deployment | **0** — never transferred, never renounced |
| Third-party label | Blockscout: "Rexas Finance: Deployer" |
| RXS held | 30,000,000 (3.00% of supply) |

The centralisation concern raised in the static study is confirmed empirically: nearly two years after deployment, with the token listed on exchanges, control still rests on a single key.

### Current state of owner privileges

| Function | Status |
|---|---|
| `enableTrading()` | **Spent** — called 2025-06-18 11:55:35 UTC; irreversible by design |
| `setWhitelist()` | Available (limited effect now that trading is open) |
| `removeStuckEth()` / `removeStuckToken()` | Available |
| `transferOwnership()` / `renounceOwnership()` | Available, never used |

Because there is no mint, no blacklist, no fee mechanism and no upgrade path, a compromise of the owner key **could not** halt the market or dilute holders. Residual exposure is limited to the 30M RXS held, assets sent to the contract, and whitelist manipulation.

---

## 3. Deployer Attribution and Funding Trail

No public identity is attributable to the owner address. The project website names no founder, team member or legal entity; CertiK reports **"Not Verified by CertiK"** (no KYC).

The only concrete attribution vector is the funding trail. **Two distinct addresses govern the system, and both were funded from Binance on the same day:**

| Address | Role | Funded | Amount | Source |
|---|---|---|---|---|
| `0x48Ee57b0…Bd018A` | token deployer / owner | 2024-08-28 11:33:35 UTC | 10.0007 ETH | Binance Hot Wallet 14 |
| `0xf6Be37a9…8d343d` | presale deployer / owner | 2024-08-28 11:47:59 UTC | 10.0200 ETH | Binance Hot Wallet 18 |

Two separate wallets, two different Binance hot wallets, near-identical amounts, **fourteen minutes apart**. This establishes a single operational cluster behind both token issuance and fundraising.

**Implication**: the operators are pseudonymous, not anonymous. Binance enforces KYC on withdrawals, so a verified legal identity exists at the exchange. It is not publicly retrievable — access requires a formal request from a competent authority. No lawful OSINT technique reaches it from outside.

---

## 4. Supply Allocation

The constructor assigns the full supply to the owner (`_balances[owner()] = _totalSupply`). Complete distribution, reconstructed from `Transfer` events:

| Date | Amount | Destination | Purpose |
|---|---|---|---|
| 2024-09-08 | 425,000,000 | `0xa9502665…` | presale contract |
| 2025-01-14 | 75,000,000 | `0xa9502665…` | presale contract |
| 2025-06-17 | 200,000,000 | `0xf28e7697…` | staking (deployed `Stake_Rexas`) |
| 2025-06-17 | 100,000,000 | `0xd2e95115…` | liquidity |
| 2025-06-17 | 100,000,000 | `0xD22D3442…` | treasury |
| 2025-06-17 | 50,000,000 | `0x15Cd1909…` | reserve |
| 2025-06-17 | 20,000,000 | `0xBdd312d6…` | reserve (never moved since) |
| — | 30,000,000 | retained by owner | team allocation |
| | **1,000,000,000** | | |

Note: `0xd2e95115…` is reported as a contract by explorers but is in fact an **EOA with an EIP-7702 delegation** (`EIP7702StatelessDeleGator`, a MetaMask smart-account implementation), not a vesting or escrow contract.

---

## 5. Presale: Capital Raised

The presale contract `0xa9502665b39b0e61F2CbbFfAD139688615fB16F6` (`Rexas_Presale`) exposes its accounting publicly. Live reads:

| Variable | Value |
|---|---|
| `overalllRaised` | **55,999,997.01 USD** (6 decimals) |
| `uniqueBuyers` | **53,910** |
| `presaleId` | 12 stages |
| `fundReceiver` | `0x6516c79E4da6AECF31f725F8a7d6709708bF6737` |
| Purchase transactions | 109,189 |

### Stage-by-stage breakdown

Decoded from `presale(uint256)`. Struct field order: `startTime, endTime, price, nextStagePrice, Sold, tokensToSell, UsdtHardcap, amountRaised, Active`.

| Stage | Period | Price | Sold | Offered | Raised |
|---|---|---|---|---|---|
| 1 | 2024-09-08 → 09-12 | $0.0300 | 14,999,986 | 15,000,000 | $450,000 |
| 2 | 2024-09-12 → 09-21 | $0.0400 | 19,999,993 | 20,000,000 | $800,000 |
| 3 | 2024-09-21 → 10-07 | $0.0500 | 29,999,997 | 30,000,000 | $1,500,000 |
| 4 | 2024-10-07 → 11-02 | $0.0600 | 44,999,999 | 45,000,000 | $2,700,000 |
| 5 | 2024-11-02 → 11-16 | $0.0700 | 44,997,746 | 45,000,000 | $3,150,000 |
| 6 | 2024-11-16 → 11-22 | $0.0800 | 45,000,000 | 45,000,000 | $3,600,000 |
| 7 | 2024-11-22 → 11-26 | $0.0900 | 44,999,990 | 45,000,000 | $4,049,999 |
| 8 | 2024-11-26 → 12-01 | $0.1000 | 45,000,000 | 45,000,000 | $4,500,000 |
| 9 | 2024-12-01 → 12-10 | $0.1250 | 44,999,998 | 45,000,000 | $5,625,000 |
| 10 | 2024-12-10 → 12-23 | $0.1500 | 44,999,999 | 45,000,000 | $6,750,000 |
| 11 | 2024-12-23 → 2025-01-16 | $0.1750 | 44,999,990 | 45,000,000 | $7,874,999 |
| 12 | from 2025-01-16 | $0.2000 | 74,999,999 | 75,000,000 | $15,000,000 |
| | | | **499,997,696** | **500,000,000** | **$55,999,997.01** |

The per-stage sum matches `overalllRaised` to the cent — two independent reads confirming each other. 99.9995% of the presale allocation was sold.

### Integrity of the counter

The obvious objection is whether the owner can inflate the figure. Source review answers it:

- `overalllRaised` is incremented **only** inside `buyWithEth()`, `buyWithUSDT()` and `buyWithUSDC()`
- there is **no administrative function** that credits purchases or tokens without a real payment — no `manualBuy`, `addUser`, `adminBuy`, `setUserData` or equivalent

The counter cannot be inflated without moving real money. **The publicly advertised raise of ~$56M is confirmed on-chain.**

---

## 6. Fund Flow

Payments never accumulate in the presale contract: they are forwarded to the collection wallet in the same transaction as the purchase (`sendValue(payable(fundReceiver), msg.value)` for ETH, direct `transferFrom` to `fundReceiver` for stablecoins). This is why the presale contract holds a zero ETH balance.

`changeFundWallet` was called **three times**, so the collection address rotated:

| Collection wallet | ETH traced | USDT traced | Balance today |
|---|---|---|---|
| `0x01fb3dcb4d5b3942ade0de7685fc86c7873f8721` | ≥ 1,753.71 | 6,442,930 | ~0 |
| `0x6d5a87623449ec6dc89d2c24e766d5e269ae8b8b` | ≥ 1,410.63 | 630,758 | 0 |
| `0x6516c79E4da6AECF31f725F8a7d6709708bF6737` | ≥ 2,146.07 | 1,426,573 | ~0.05 |
| **Total traced** | **≥ 5,310.41 ETH** | **≥ 8,500,261 USDT** | **all drained** |

**USDC: zero.** Although `buyWithUSDC()` exists and is callable, the channel was never used.

> These totals are **lower bounds**. Roughly one fifth of the 109,189 purchase transactions could be reconstructed before hitting explorer pagination limits. The gap against $56M is an artefact of the measurement, **not evidence of a shortfall**.

---

## 7. Pre-Listing Window

Because the contract launches with trading disabled, only whitelisted addresses could move tokens before `enableTrading()`. The whitelist is therefore the decisive observation point.

### Whitelist grants

| Timestamp (UTC) | Address | Context |
|---|---|---|
| 2024-09-08 17:08 | `0xa9502665…` | presale contract (required to deliver tokens) |
| 2025-06-17 13:29 | `0xd2e95115…` | received 100M RXS 11 minutes earlier |
| 2025-06-17 13:30 | `0xf28e7697…` | received 200M RXS |
| 2025-06-17 13:31 | `0xBdd312d6…` | received 20M RXS |
| 2025-06-17 13:34 | `0xD22D3442…` | received 100M RXS |
| 2025-06-17 13:35 | `0x15Cd1909…` | received 50M RXS |

### Timeline

- **2025-06-17 13:18–13:35 UTC** — 470M RXS distributed to five wallets, all whitelisted
- **2025-06-18 11:55:35 UTC** — `enableTrading()` — market opens for everyone
- **2025-06-19** — public listing on MEXC, BitMart and LBank at $0.25

Movements of `0xd2e95115…` (liquidity allocation) inside the window:

| Timestamp (UTC) | Amount | Destination | Market status |
|---|---|---|---|
| 2025-06-17 13:41:23 | 80,000 RXS | `0xd9ab439a…` | **closed** |
| 2025-06-17 16:03:59 | 40 RXS | `0xbe86abaa…` | **closed** |
| 2025-06-18 08:12:59 | 50 RXS | `0x06d4d0b7…` | **closed** |
| 2025-06-18 08:37:47 | **1,000,000 RXS** | `0x06d4d0b7…` | **closed** |
| 2025-06-18 16:06:59 | 2,000,000 RXS | `0x22ef32af…` | open |
| 2025-06-18 16:12:11 | 5,000,000 RXS | `0x163052747…` | open |
| 2025-06-18 17:00:59 | 10,000,000 RXS | `0x06d4d0b7…` | open |
| 2025-06-19 08:02:59 | 2,500,000 RXS | `0xcd4c0ddc…` | listing day |

The first transfer occurs **12 minutes after** the whitelist grant and **22 hours before** trading opens. The one-million-token transfer leaves **3 hours 18 minutes before** the market opens to the public.

### What did and did not happen

**No sale preceded the market.** Two findings rule it out:

- the Uniswap V3 pool was **created on 2025-08-02**, six weeks *after* listing — no DEX venue existed earlier
- the first deposits into the MEXC hot wallet are all timestamped **2025-06-19 11:11**, alongside those of hundreds of small presale participants; this is the exchange processing deposits, not privileged access

**A pre-positioning did occur.** The whitelist privilege was used to stage 1,000,050 RXS on an exchange deposit wallet while every other holder was frozen. The advantage obtained is one of **timing, not price**: no one could sell earlier, because no market existed earlier.

---

## 8. Post-Listing Distribution

`0x06d4d0b7a22aab6bc0738c118412c99368e57808` is the central routing node — an untagged EOA holding a negligible ETH balance, the typical profile of an exchange deposit wallet. Tracing confirms the function: it **received 165,500,050 RXS** from team wallets and forwarded **all of it**, to the last token, to `0x9642b23Ed1E01Df1092B92641051881a322F5D4E` (**MEXC 21** hot wallet).

| Date | Deposited to MEXC |
|---|---|
| 2025-06-19 11:11 | 11,000,050 |
| 2025-08-06 | 40,000,000 |
| 2025-09-18 | 25,000,000 |
| 2025-10-06 | 16,250,000 |
| 2025-10-27 | 48,750,000 |
| 2026-01-08 | 15,000,000 |
| 2026-01-12 | 9,500,000 |
| **Total** | **165,500,050 RXS = 16.55% of supply** |

The same wallet had previously received **650,000 USDT** from the presale `fundReceiver`, making it a shared hub for both stablecoin proceeds and tokens destined for exchange sale.

---

## 9. Market Depth Analysis

A recurring question about this token is how the price could collapse given a $56M raise. The on-chain data answers it, and the answer rests on a distinction that is frequently conflated.

### Raised capital is not market liquidity

Each payment was forwarded to the collection wallet at purchase time, and all three collection wallets are now drained. **That capital left the system**; nothing ties it to the token price.

| Quantity | Value |
|---|---|
| Raised — real money, collected, withdrawn | $55,999,997 |
| Market capitalisation at listing — supply × last traded price | $250,000,000 (notional) |
| Liquidity provided to the DEX pool | **$100,000** |

Market capitalisation is not money in existence: it is supply multiplied by the last traded price.

### Sell-side asymmetry

At listing, 500M tokens were held by 53,910 participants, and **all of them were in profit**. Average presale price is $0.112 against a $0.25 opening.

| Entry price | Stage | Position at listing |
|---|---|---|
| $0.030 | stage 1 | **+733%** |
| $0.112 | presale average | +123% |
| $0.200 | stage 12 | +25% |

No holder had a reason to hold; every holder had a reason to sell. This requires no bad faith — it is the rational response to a three-digit gain on an illiquid asset.

### Pool measurements

The Uniswap V3 pool is **RXS/USDT** (0.3% fee tier), `0x557520519449BAA1E2d4D4Ad4CA0A23DC3fD6ec1`:

| | At creation (2025-08-02) | Current |
|---|---|---|
| USDT | 100,000 | **8,943** |
| RXS | 31,798,661 | 22,609,510 |

**91% of the stablecoin side was drained by sellers.** Spread across 53,910 buyers, each selling **$1.69** worth of tokens would have emptied it entirely.

The notional value of presale-held tokens ($125M) against provided liquidity ($100,000) is a ratio of roughly **1,250 : 1**.

### Chronology

The pool was created six weeks after listing at a deposit ratio implying a price near **$0.003** — already about **−98.7%** from the $0.25 opening. The collapse did not occur on the decentralised venue: it had **already happened on centralised exchanges within the first weeks**.

*(In Uniswap V3 liquidity is range-concentrated, so the deposit ratio indicates an order of magnitude, not an exact price. CEX order-book depth — where most trading occurred — is not observable on-chain.)*

Liquidity provisioning amounted to **0.18% of the raised capital**. At 10% ($5.6M) the pool would have been roughly 56× deeper.

---

## 10. Tokenomics Compliance

On-chain allocation was compared against the publicly published tokenomics. It matches, line by line:

| Published allocation | Share | On-chain address | Result |
|---|---|---|---|
| Presale 50% | 500M | `0xa9502665…` | ✅ exact |
| Staking 20% | 200M | `0xf28e7697…` (deployed `Stake_Rexas`) | ✅ exact |
| Liquidity 10% | 100M | `0xd2e95115…` (31.8M placed in Uniswap) | ✅ exact |
| Treasury 10% | 100M | `0xD22D3442…` | ✅ exact |
| Team 3% | 30M | owner wallet — **never moved** | ✅ exact |
| Remainder 7% | 50M + 20M | `0x15Cd1909…`, `0xBdd312d6…` (latter never moved) | ✅ exact |

The 30M team allocation, subject to a declared 36-month vesting schedule, is **still untouched** more than a year after listing. That commitment is being honoured.

Tokens that fed exchange sales came from **treasury, liquidity and reserve** allocations, for which no lock commitment is documented.

---

## 11. Findings Summary

Severity ratings follow the repository's scale. Note that these are **not code vulnerabilities** — the contract contains no exploitable defect. They are centralisation and conduct findings, rated by potential impact on holders.

| # | Finding | Severity |
|---|---|---|
| 1 | Ownership held by a single EOA, never migrated to a multisig or timelock, ~2 years post-deployment | **Medium** |
| 2 | 16.55% of supply routed to a single exchange over 7 tranches, creating sustained unilateral sell pressure | **Medium** |
| 3 | Liquidity provisioning of 0.18% of raised capital against a 1,250:1 notional-to-liquidity ratio | **Medium** |
| 4 | Whitelist privilege used to stage tokens on an exchange deposit wallet before trading opened | **Low** |
| 5 | Fully anonymous team, no KYC with any verifier; identity recoverable only via legal process | **Low** |
| 6 | Public "100% Secure & Verified By CertiK" claim against 2 unresolved Major centralisation findings and an auditor-declared absence of KYC | **Informational** |
| 7 | `buyWithUSDC()` exposed but never used — unnecessary attack surface | **Informational** |

### Mitigating factors verified on-chain

- No mint function; supply fixed at construction
- No blacklist, no transfer fee, no pause mechanism
- No proxy or upgrade path — bytecode is immutable
- `enableTrading()` is one-way and already spent, so it cannot be weaponised
- Tokens were actually delivered: 499,997,696 of 500,000,000
- Liquidity and staking contracts were actually deployed and funded
- Team vesting commitment observed

---

## 12. Assessment

The on-chain record does not match an exit-scam profile. In that pattern one expects undelivered tokens, no listing, absent liquidity, and allocations diverging from the published plan. Here, token delivery, listing, liquidity provisioning, staking deployment and tokenomics compliance are all present and documented, and the contract contains no backdoor.

What the record does show is a project that raised substantial capital from a large retail base, built the promised infrastructure, and subsequently routed a significant share of its treasury and reserve allocations to a centralised exchange while the price declined by more than 99% from the listing level.

Whether that conduct constitutes a violation is **not determinable from chain data**. It depends on the binding content of representations made during the offering, on whether lock commitments existed for treasury and liquidity allocations, on the accuracy of promotional claims, and on the applicable regulatory framework. Anyone who believes they suffered a loss should approach a competent authority; as documented in section 3, the operators' real identity is reachable only through a formal request to Binance.

This section is an argued interpretation of the evidence, offered separately from the verified facts in sections 2–10.

---

## 13. Reproducing These Findings

No API key is required. Foundry `cast` is needed for the typed contract reads.

```bash
RXS=0x9eAeBd7E73D97E78c77fAB743e6FFA1b550e224c
PRESALE=0xa9502665b39b0e61F2CbbFfAD139688615fB16F6
R=https://ethereum-rpc.publicnode.com
```

**Ownership status**

```bash
cast call $RXS "owner()(address)" --rpc-url $R

# Ownership transfer history from the deployment block (0x13BDF42 = 20700162)
curl -s -X POST $R -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"address":"'"$RXS"'","topics":["0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0"],"fromBlock":"0x13BDF42","toBlock":"latest"}]}'
```

**Presale accounting**

```bash
cast call $PRESALE "overalllRaised()(uint256)" --rpc-url $R   # divide by 1e6 for USD
cast call $PRESALE "uniqueBuyers()(uint256)"   --rpc-url $R
cast call $PRESALE "presaleId()(uint256)"      --rpc-url $R
cast call $PRESALE "fundReceiver()(address)"   --rpc-url $R

# Per-stage data; struct order given in section 5
cast call $PRESALE "presale(uint256)" 12 --rpc-url $R
```

**Supply allocation and funding trail**

```bash
# Every RXS transfer in or out of the owner wallet
curl -s "https://eth.blockscout.com/api/v2/addresses/0x48Ee57b01D226d1E1efAE1Fb15f45D9A11Bd018A/token-transfers?token=$RXS"

# Inbound transactions to the owner — reveals the Binance funding
curl -s "https://eth.blockscout.com/api/v2/addresses/0x48Ee57b01D226d1E1efAE1Fb15f45D9A11Bd018A/transactions?filter=to"

# Same for the presale deployer
curl -s "https://eth.blockscout.com/api/v2/addresses/0xf6Be37a90E6c996A6f75f58067cB845c0c8d343d/transactions?filter=to"
```

**Pre-listing window and exchange routing**

```bash
# Whitelist grants and enableTrading — read the decoded_input field
curl -s "https://eth.blockscout.com/api/v2/addresses/0x48Ee57b01D226d1E1efAE1Fb15f45D9A11Bd018A/transactions?filter=from"

# The hub that fed MEXC: everything in, everything out
curl -s -A "Mozilla/5.0" "https://eth.blockscout.com/api?module=account&action=tokentx&address=0x06d4d0b7a22aab6bc0738c118412c99368e57808&contractaddress=$RXS&sort=asc&offset=100&page=1"
```

**Pool depth**

```bash
POOL=0x557520519449BAA1E2d4D4Ad4CA0A23DC3fD6ec1
cast call $POOL "token0()(address)" --rpc-url $R
cast call $POOL "token1()(address)" --rpc-url $R
cast call $RXS "balanceOf(address)(uint256)" $POOL --rpc-url $R
cast call 0xdAC17F958D2ee523a2206206994597C13D831ec7 "balanceOf(address)(uint256)" $POOL --rpc-url $R
```

---

## 14. Corrections to the Static Study

Per the contributing guidelines, original findings are preserved; the following data points are corrected here with their date. These do not affect the conclusions of the companion document.

**2026-08-28**

1. **Compiler version.** The static study lists `^0.8.20` (the pragma). The verified deployed build is **`0.8.26+commit.8a97fa7a`**, EVM version Cancun, optimiser disabled.
2. **"Verification Date: 2024-09-07".** That timestamp is the **deployment** date (block 20700162, 17:17:11 UTC), not the source-verification date.
3. **Recommendation "Renounce Ownership".** As of this analysis ownership has *not* been renounced, and renouncement would now permanently disable `removeStuckEth`/`removeStuckToken`, stranding any assets subsequently sent to the contract. Migrating ownership to a multisig is the safer remedy and addresses the same centralisation finding.
4. **Recommendation "Security Audit".** An audit exists: CertiK, delivered 2024-11-12 — 0 Critical, 0 Medium, **2 Major centralisation findings, both acknowledged and unresolved**, 3 Minor, 1 Informational; formal verification 32/32 properties. The auditor separately reports the team as not KYC-verified.

---

## 15. References

**On-chain**

- [Token contract](https://etherscan.io/address/0x9eaebd7e73d97e78c77fab743e6ffa1b550e224c) · [Blockscout](https://eth.blockscout.com/address/0x9eAeBd7E73D97E78c77fAB743e6FFA1b550e224c)
- [Owner / deployer `0x48Ee57b0…`](https://eth.blockscout.com/address/0x48Ee57b01D226d1E1efAE1Fb15f45D9A11Bd018A)
- [Presale contract `0xa9502665…`](https://eth.blockscout.com/address/0xa9502665b39b0e61F2CbbFfAD139688615fB16F6)
- [Presale deployer `0xf6Be37a9…`](https://eth.blockscout.com/address/0xf6Be37a90E6c996A6f75f58067cB845c0c8d343d)
- [Final collection wallet `0x6516c79E…`](https://eth.blockscout.com/address/0x6516c79E4da6AECF31f725F8a7d6709708bF6737)
- [MEXC routing hub `0x06d4d0b7…`](https://eth.blockscout.com/address/0x06d4d0b7a22aab6bc0738c118412c99368e57808)
- [Uniswap V3 RXS/USDT pool](https://eth.blockscout.com/address/0x557520519449BAA1E2d4D4Ad4CA0A23DC3fD6ec1)

**Audit and project**

- [CertiK Skynet — Rexas Finance](https://skynet.certik.com/projects/rexas-finance)
- [Project website](https://rexas.com/) · [Audit page](https://rexas.com/audit/)
- [Listing announcement — MEXC, BitMart, LBank](https://coinpedia.org/press-release/official-announcement-rexas-finance-listing-on-mexc-bitmart-and-lbank/)
- [Published tokenomics](https://www.bitrue.com/blog/rexas-finance-tokenomics-rxs-token)

---

## Disclaimer

This analysis is for educational purposes, consistent with the repository's stated scope. It is based on public blockchain data and open sources, and is not affiliated with Rexas Finance, CertiK or any exchange named. On-chain data reflects chain state at the analysis date and may since have changed. Sections 2–10 present verifiable, reproducible facts with limitations stated in context; sections 11 and 12 are analytical judgements, marked as such. Nothing here constitutes financial, investment or legal advice, nor a legal characterisation of any conduct described.

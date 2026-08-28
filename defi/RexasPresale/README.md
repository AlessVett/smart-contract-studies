# Rexas Presale

## Overview
- **Contract Address**: 0xa9502665b39b0e61F2CbbFfAD139688615fB16F6
- **Network**: Ethereum Mainnet
- **Contract Name**: `Rexas_Presale`
- **Purpose**: Multi-stage token sale for [RXS](../../tokens/RXS/), accepting ETH, USDT and USDC

## Files in this Directory
- `rexas_presale.sol` - Original contract source code
- `rexas_presale_detailed_study.md` - Security analysis with on-chain verification

## Key Features
- 12 sale stages with per-stage pricing and hardcaps
- USD pricing via a Chainlink feed; ETH converted at purchase time
- Immediate token delivery — no claim step, no vesting held by the contract
- Funds forwarded to a collection wallet on every purchase; never custodied
- `nonReentrant` on all purchase paths, with checks-effects-interactions respected

## On-Chain Record (as of 2026-08-28)
- **Raised**: $55,999,997.01 from **53,910 unique buyers** across 109,189 purchases
- **Sold**: 499,997,696 of 500,000,000 RXS (99.9995%)
- **Collection wallet**: rotated 3 times via `changeFundWallet`; all now drained
- **USDC purchases**: zero — the channel exists but was never used
- **Owner**: `0xf6Be37a90E6c996A6f75f58067cB845c0c8d343d`, a single EOA

## Findings
1 High · 4 Medium · 2 Low · 2 Informational

The accounting is sound and the purchase paths are well built. Risk is
concentrated in owner privilege: the price oracle, the sale token and the
stablecoin addresses are all replaceable at will, without timelock or events.
None of those powers were ever exercised.

**L-01 has already materialised**: `WithdrawTokens` cannot recover USDT, and
46.85 USDT sit permanently stuck in the contract — the same defect the RXS token
carries in `removeStuckToken`.

**No audit covers this contract.** The CertiK audit the project advertises
examined the ERC20 token, which never custodied funds. The contract that handled
$56 million was not audited.

## Related
- [Token study](../../tokens/RXS/) — RXS, the asset sold here
- [`tools/onchain_profile.py`](../../tools/onchain_profile.py) — reproduces the
  L-01 finding automatically

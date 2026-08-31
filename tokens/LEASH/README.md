# LEASH (Doge Killer)

## Overview
- **Contract Address**: 0x27C70Cd1946795B66be9d954418546998b546634
- **Network**: Ethereum Mainnet
- **Contract Name**: `UFragments` — Ampleforth-derived elastic supply token
- **Token Symbol**: LEASH
- **Decimals**: 18

## Files in this Directory
- `leash.sol` - Original contract source code
- `leash_detailed_study.md` - Security analysis of the rebase mechanism and control chain

## Key Features
- **Elastic supply**: balances stored in a hidden "gon" denomination, rescaled by rebases
- Rebases proportional — relative ownership never changes
- Driven by an automated monetary policy reading a median price oracle
- Daily rebase window, damped by `rebaseLag = 10`
- Supply capped at `MAX_SUPPLY = 2**128 - 1`

## On-Chain Record (as of 2026-08-31)
- **315 rebase events** in two disconnected episodes
- 2020: four contractions, ending at **107,646.85 tokens**
- Then **12,277,495 blocks of dormancy** — nearly five years
- 2025-08-11 → 2026-06-25: **311 consecutive expansions**, ~+10% each
- **Current supply: 803,760,032,105,055,232** — roughly 7.5 trillion× the 2020 floor
- Rebases currently blocked: the oracle returns `(0, false)` and the policy requires a valid rate
- Headroom to the cap: **423×**, about 63 further rebases

## Findings
2 High · 2 Medium · 1 Low · 2 Informational

The defining issue is the **control chain asymmetry**. Ownership is renounced on
the token, the policy and the orchestrator — so `setRebasePaused`,
`setMonetaryPolicy` and `setTokenPaused` are permanently unreachable. The oracle
alone retains a live owner, and with `minimumProviders = 1` that owner can
register a provider and restart the expansion.

**One party can restart it; nobody can stop it.** The circuit breaker exists,
reads `false`, and can never be engaged.

Rebases are proportional, so no holder is diluted relative to another. The harm
is that every off-chain representation of this token is wrong — market data
still reports the 2020 supply figure, understating reality by about twelve
orders of magnitude — and that a supply-critical control rests on a single key
while every corrective control has been destroyed.

## Why This Study Exists
It began as a data anomaly: [`tools/onchain_profile.py`](../../tools/onchain_profile.py)
reported a supply twelve orders of magnitude above every published figure. The
tool was right. The tool now detects elastic supply and says so.

## Related
- [`tools/onchain_profile.py`](../../tools/onchain_profile.py) — flags elastic supply automatically
- [RXS study](../RXS/) — where the "renouncing ownership is not always safe"
  thread first appeared, in a much milder form

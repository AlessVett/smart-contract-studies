# Rexas Finance (RXS) Token

## Overview
- **Contract Address**: 0x9eAeBd7E73D97E78c77fAB743e6FFA1b550e224c
- **Network**: Ethereum Mainnet
- **Token Symbol**: RXS
- **Total Supply**: 1,000,000,000 RXS

## Files in this Directory
- `rxs.sol` - Original contract source code
- `rxs_detailed_study.md` - Static analysis: what the code can do
- `rxs_onchain_analysis.md` - On-chain analysis: what actually happened (2026-08-28)

## Key Features
- Standard ERC20 implementation
- Whitelist system for pre-launch control
- Trading enable/disable mechanism
- Owner functions for stuck fund recovery

## On-Chain Status (as of 2026-08-28)
- **Owner**: `0x48Ee57b01D226d1E1efAE1Fb15f45D9A11Bd018A` — single EOA, also the deployer; ownership never transferred or renounced
- **Deployed**: 2024-09-07, block 20700162
- **Trading enabled**: 2025-06-18 (irreversible); public listing 2025-06-19
- **Presale raised**: $55,999,997 from 53,910 buyers across 12 stages, verified on-chain
- **Audit**: CertiK, 2024-11-12 — 2 Major centralisation findings, acknowledged and unresolved; team not KYC-verified

See `rxs_onchain_analysis.md` for the full evidence and reproduction commands.

## Links
- Website: https://rexas.com
- Twitter: https://x.com/rexasfinance
- Telegram: https://t.me/rexasfinance
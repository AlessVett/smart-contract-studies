# Detailed Study of RXS.sol Contract

> **Scope.** This document is the **static analysis**: what the source code can do.
> For deployed behaviour — ownership status, capital raised, fund flow, market
> activity — see [`rxs_onchain_analysis.md`](./rxs_onchain_analysis.md).

## Executive Summary

REXAS_FINANCE is a fixed-supply ERC20 token with two launch-control features: a
one-way trading switch and an owner-managed whitelist. It contains **no mint
function, no blacklist, no transfer fee, no pause mechanism and no upgrade
path**. The absence of these is the contract's main security strength: the
owner cannot dilute holders, freeze balances or tax transfers.

The residual risk is concentrated in **access control and recovery functions**,
not in the token accounting, which is a conventional and correct ERC20
implementation.

### Severity Breakdown

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 0 |
| Medium | 1 |
| Low | 2 |
| Informational | 5 |

See [section 10](#10-findings-register) for the full register.

### Key Recommendations

1. **Transfer ownership to a multisig.** The single-key owner is the highest-impact
   finding. Note that *renouncing* ownership — a common suggestion — would
   permanently disable the recovery functions; migration is the safer remedy.
2. **Emit events for `setWhitelist` and `enableTrading`.** Both change
   security-relevant state with no on-chain signal for monitoring tools.
3. **Use a safe-transfer wrapper in `removeStuckToken`.** As written it cannot
   recover non-compliant tokens such as USDT — see finding L-01, which has
   already materialised on the deployed contract.

### Audit History

| Auditor | Date | Result |
|---|---|---|
| CertiK | 2024-11-12 | 0 Critical, 0 Medium, **2 Major (centralisation, acknowledged — unresolved)**, 3 Minor, 1 Informational. Formal verification 32/32 properties. Team **not** KYC-verified. |

---

## 1. Contract Overview

### Basic Information
- **Token Name**: Rexas Finance
- **Symbol**: RXS
- **Contract Address**: 0x9eAeBd7E73D97E78c77fAB743e6FFA1b550e224c
- **Solidity Version**: ^0.8.20
- **License**: MIT
- **Verification Date**: 2024-09-07 (on Etherscan)

### Project Metadata
- **Website**: https://rexas.com
- **Twitter/X**: https://x.com/rexasfinance
- **Telegram**: https://t.me/rexasfinance

### Token Specifications
- **Decimals**: 18
- **Total Supply**: 1,000,000,000 RXS (1 billion tokens)
- **Standard**: ERC20

## 2. Contract Architecture

### Inheritance Structure
```
Context
    └── Ownable
            └── REXAS_FINANCE (implements IERC20)
```

### Contracts and Interfaces
1. **IERC20**: Standard ERC20 interface (lines 25-55)
2. **IDexFactory**: Interface for creating DEX trading pairs (lines 58-63)
3. **IDexRouter**: Interface for DEX router (lines 66-90)
4. **Context**: Abstract contract for getting sender information (lines 92-101)
5. **Ownable**: Contract ownership management (lines 103-138)
6. **REXAS_FINANCE**: Main token contract (lines 140-296)
7. **SafeMath**: Library for safe mathematical operations (lines 298-363)

## 3. State Variables

### Mappings
- `mapping(address => uint256) private _balances`: Token balances by address
- `mapping(address => mapping(address => uint256)) private _allowances`: Approvals for delegated transfers
- `mapping(address => bool) public whitelist`: Whitelist to bypass trading restrictions

### Variables
- `string private _name = "Rexas Finance"`: Token name
- `string private _symbol = "RXS"`: Token symbol
- `uint8 private _decimals = 18`: Token decimals
- `uint256 private _totalSupply = 1_000_000_000 * 1e18`: Total supply (1 billion)
- `bool public trading`: Flag to enable/disable trading

## 4. Core Functions

### Constructor (lines 155-160)
- Adds deployer to whitelist
- Assigns all tokens to owner
- Emits Transfer event

### Public View Functions
- `name()`: Returns token name
- `symbol()`: Returns token symbol
- `decimals()`: Returns decimals
- `totalSupply()`: Returns total supply
- `balanceOf(address)`: Returns balance of an address
- `allowance(address, address)`: Returns approved amount

### Transfer Functions
- `transfer(address, uint256)`: Standard ERC20 transfer
- `transferFrom(address, address, uint256)`: Delegated transfer
- `approve(address, uint256)`: Approve amount for delegated transfer
- `increaseAllowance(address, uint256)`: Increase allowance
- `decreaseAllowance(address, uint256)`: Decrease allowance

### Admin Functions (Owner Only)
- `enableTrading()`: Enable trading (irreversible)
- `setWhitelist(address, bool)`: Manage whitelist
- `removeStuckEth(address)`: Recover stuck ETH from contract
- `removeStuckToken(address, address, uint256)`: Recover stuck ERC20 tokens

### ETH Reception Function
- `receive() external payable`: Allows contract to receive ETH

## 5. Transfer Logic (_transfer)

The `_transfer` function (lines 277-294) implements the main logic:

1. **Validations**:
   - Verifies addresses are not zero
   - Verifies amount is greater than zero

2. **Trading Control**:
   - If neither sender nor recipient are whitelisted
   - Trading must be enabled

3. **Execution**:
   - Subtracts amount from sender
   - Adds amount to recipient
   - Emits Transfer event

## 6. Security and Access Control

### Security Mechanisms
1. **onlyOwner Modifier**: Restricts access to critical functions
2. **Whitelist System**: Allows transfers before trading is enabled
3. **Trading Lock**: Once enabled, trading cannot be disabled
4. **SafeMath**: Prevents overflow/underflow in mathematical operations

### Validation Checks
- Zero addresses not allowed
- Amounts must be greater than zero
- Sufficient balances for transfers
- Sufficient allowance for transferFrom

## 7. Potential Vulnerabilities and Considerations

### Strengths
1. **Simplicity**: Standard ERC20 implementation without excessive complexity
2. **SafeMath**: Protection against mathematical overflows
3. **Whitelist**: Initial control over transfers
4. **Recovery Functions**: Ability to recover stuck funds

### Potential Risks
1. **Centralization**: Owner has significant control:
   - Can manage whitelist
   - Can recover any tokens or ETH from contract
   - Can enable trading

2. **Missing DEX Functionality**: 
   - IDexFactory and IDexRouter interfaces are defined but not used
   - No automatic liquidity or swap implemented

3. **No Fee Mechanism**: 
   - Contract doesn't implement transfer taxes or fees

4. **Permanent Whitelist**: 
   - Whitelisted addresses always bypass trading check

### Recommendations
1. **Renounce Ownership**: After launch, consider renouncing ownership for decentralization
2. **Security Audit**: Submit contract for professional audit
3. **Timelock**: Implement timelock for administrative functions
4. **Additional Events**: Add events for whitelist operations

## 8. Gas Optimization

The contract uses some optimizations:
- SafeMath for Solidity <0.8.0 (not necessary in 0.8.20 but kept for compatibility)
- State variables grouped to optimize storage
- Use of `payable` for functions handling ETH

## 9. Conclusions

The RXS.sol contract is a relatively standard ERC20 implementation with some additional features for launch control:
- Whitelist system for pre-launch
- Trading enablement mechanism
- Fund recovery functions

It's a solid contract for a basic utility token, but requires attention to centralization and could benefit from additional features for DEX integration and decentralized governance mechanisms.

---

## 10. Findings Register

*Added 2026-08-28. Findings consolidate the observations in sections 6–7 above, assign severity per the repository scale, and add issues identified in a subsequent deep-dive review. No earlier finding has been removed.*

| ID | Finding | Severity |
|---|---|---|
| M-01 | Ownership held by a single EOA with unrevoked administrative powers | Medium |
| L-01 | `removeStuckToken` cannot recover non-ERC20-compliant tokens | Low |
| L-02 | `removeStuckEth` uses `.transfer()` and its 2300 gas stipend | Low |
| I-01 | No events emitted by `setWhitelist` or `enableTrading` | Informational |
| I-02 | Whitelist entries persist indefinitely unless explicitly revoked | Informational |
| I-03 | SafeMath is redundant under Solidity 0.8+ | Informational |
| I-04 | Token metadata held in mutable storage rather than constants | Informational |
| I-05 | Unused DEX interfaces and a misleading `receive()` comment | Informational |

---

### M-01 — Single-key ownership with unrevoked powers · Medium

**Description.** `Ownable` grants one address control over `enableTrading`, `setWhitelist`, `removeStuckEth`, `removeStuckToken` and ownership transfer itself. The owner is a plain EOA — a single private key, with no multisig or timelock.

**Impact.** Compromise of that key exposes: any assets held by the contract, and the ability to grant whitelist exemptions. It does **not** allow minting, freezing balances, taxing transfers or upgrading code, none of which exist. `enableTrading` is one-way and, on the deployed contract, already spent — so trading cannot be re-disabled by anyone, including a key thief.

**Evidence.** Confirmed on the deployed contract: `owner()` still returns the deployer address, and the only `OwnershipTransferred` event is the constructor's initialisation (`0x0` → deployer) at block 20700162 — no transfer has occurred since. See `rxs_onchain_analysis.md` §2.

**Recommendation.** Transfer ownership to a multisig. Do **not** renounce it: renouncement would permanently strand any assets later sent to the contract by disabling both recovery functions.

---

### L-01 — `removeStuckToken` cannot recover non-compliant tokens · Low

**Description.** The recovery function calls the token through an interface declaring a boolean return:

```solidity
function removeStuckToken(address _token, address _receiver, uint256 _amount) public onlyOwner {
    IERC20(_token).transfer(_receiver, _amount);
}
```

Tokens that predate strict ERC20 conformance — USDT being the most widespread — return no data from `transfer`. Under Solidity 0.8 the ABI decoder expects 32 bytes of return data, finds none, and reverts. The return value is also unchecked, so a token returning `false` instead of reverting would fail silently.

**Impact.** Affected tokens sent to the contract are **permanently unrecoverable**. This is not hypothetical: the deployed contract currently holds **2,320.36 USDT** that cannot be withdrawn by anyone.

**Proof of concept.** Simulated against mainnet state, called from the owner address:

```bash
OWNER=0x48Ee57b01D226d1E1efAE1Fb15f45D9A11Bd018A
RXS=0x9eAeBd7E73D97E78c77fAB743e6FFA1b550e224c

# USDT — non-compliant, returns no data
cast call $RXS "removeStuckToken(address,address,uint256)" \
  0xdAC17F958D2ee523a2206206994597C13D831ec7 $OWNER 1000000 \
  --from $OWNER --rpc-url https://ethereum-rpc.publicnode.com
# → execution reverted

# ENS — compliant, returns bool
cast call $RXS "removeStuckToken(address,address,uint256)" \
  0xC18360217D8F7Ab5e7c516566761Ea12Ce7F9D72 $OWNER 1000000000000000000 \
  --from $OWNER --rpc-url https://ethereum-rpc.publicnode.com
# → 0x  (success)
```

**Recommendation.** Use OpenZeppelin's `SafeERC20.safeTransfer`, which tolerates both empty and boolean returns and reverts on an explicit `false`.

---

### L-02 — `removeStuckEth` uses `.transfer()` · Low

**Description.** `payable(_receiver).transfer(address(this).balance)` forwards a fixed 2300 gas stipend.

**Impact.** Recovery to a contract address fails whenever the recipient's `receive`/`fallback` costs more than 2300 gas — a threshold that also shifts with gas-cost repricing across network upgrades. Recovery to an EOA is unaffected. The deployed contract currently holds 0.131 ETH.

**Recommendation.** Use `(bool ok, ) = _receiver.call{value: amount}(""); require(ok);`, with a reentrancy guard if the function is ever extended beyond `onlyOwner`.

---

### I-01 — No events on privileged state changes · Informational

**Description.** `setWhitelist` and `enableTrading` mutate security-relevant state without emitting events.

**Impact.** Off-chain monitoring cannot subscribe to whitelist or trading-status changes; they are observable only by decoding calldata or polling state. On the deployed contract this obscured a materially relevant sequence — whitelist grants issued the day before trading opened. See `rxs_onchain_analysis.md` §7.

**Recommendation.** Emit `WhitelistUpdated(address indexed user, bool exempt)` and `TradingEnabled(uint256 timestamp)`.

---

### I-02 — Whitelist entries are permanent until revoked · Informational

**Description.** `whitelist[address]` has no expiry. Entries granted for launch remain in force indefinitely.

**Impact.** Limited once trading is enabled, since the whitelist only bypasses the trading gate and that gate is open to everyone. The exposure is confined to the pre-launch window, where a whitelisted address can transact while all other holders are frozen.

**Recommendation.** Either revoke entries after launch, or scope the check so it is inert once `trading` is true.

---

### I-03 — SafeMath is redundant · Informational

**Description.** The contract declares `using SafeMath for uint256` while compiling under `pragma solidity ^0.8.20`. Arithmetic overflow and underflow have reverted natively since 0.8.0.

**Impact.** Every `.add()` and `.sub()` performs a redundant conditional on top of the compiler's own check. It costs gas on every transfer and inflates deployed bytecode. There is no correctness issue — the behaviour is safe, merely doubly enforced.

**Recommendation.** Drop the library and use native operators. Where a custom revert message is wanted on subtraction, an explicit `require` before the operation is cheaper than the SafeMath path.

---

### I-04 — Token metadata in mutable storage · Informational

**Description.** `_name`, `_symbol`, `_decimals` and `_totalSupply` are plain state variables assigned at declaration, never modified afterwards.

**Impact.** Each read performs an `SLOAD` (2100 gas cold, 100 warm) where a `constant` would be inlined at compile time and an `immutable` read from bytecode. `totalSupply()` and `decimals()` are called frequently by integrators, so the cost recurs indefinitely. Storage slots are also consumed unnecessarily.

**Recommendation.** Declare all four as `constant`. Note this is not upgradeable on the deployed instance — it is guidance for future contracts.

---

### I-05 — Unused DEX interfaces and misleading comment · Informational

**Description.** `IDexFactory` and `IDexRouter` are declared (lines 58–90) and never instantiated. `receive()` carries the comment *"to receive ETH from dexRouter when swapping"*, but no router integration exists.

**Impact.** No gas cost — unreferenced interfaces generate no bytecode. The issue is comprehension: a reader, or an automated classifier, may infer swap or auto-liquidity behaviour that the contract does not implement. The `receive()` function does accept ETH from any sender, recoverable only by the owner and subject to L-02.

**Recommendation.** Remove the unused interfaces and correct the comment to state that ETH is accepted only for recovery.

---

## 11. Gas Analysis (Measured)

Section 8 discusses optimization qualitatively. Measured figures from the deployment transaction (`0x496ab249…ea2ac5`, block 20700162):

| Metric | Value |
|---|---|
| Deployment gas used | 2,068,460 |
| Gas price paid | 1.461 gwei |
| Deployment cost | 0.003023 ETH |

Optimization was **disabled** in the verified build (`0.8.26+commit.8a97fa7a`, EVM Cancun). Enabling the optimizer, dropping SafeMath (I-03) and making metadata `constant` (I-04) would each reduce both deployment and per-transfer cost. These are recorded for future contracts; the deployed bytecode is immutable.

---

## 12. Verification Status

| Check | Result |
|---|---|
| Source verified on explorers | Yes |
| Repository copy matches on-chain source | **Yes** — identical after normalising whitespace and the explorer's verification header |
| Compiler (verified build) | `0.8.26+commit.8a97fa7a`, EVM Cancun, optimizer disabled |
| Pragma declared in source | `^0.8.20` |
| Proxy / upgradeable | No — no implementation slot, bytecode immutable |
| Test suite in repository | None |

**Note on the compiler.** Section 1 lists the Solidity version as `^0.8.20`, which is the *pragma*. The build actually deployed and verified used **0.8.26**. Both statements are accurate about different things; the distinction matters when reproducing the bytecode.

**Note on the date.** The "Verification Date: 2024-09-07" in section 1 is the **deployment** timestamp (block 20700162, 17:17:11 UTC).

To reproduce the source comparison:

```bash
curl -s "https://eth.blockscout.com/api/v2/smart-contracts/0x9eAeBd7E73D97E78c77fAB743e6FFA1b550e224c" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['source_code'])" > onchain.sol

# Compare ignoring whitespace and the explorer's verification banner
diff -w -B <(grep -v 'Submitted for verification' onchain.sol) \
           <(grep -v 'Submitted for verification' rxs.sol)
```
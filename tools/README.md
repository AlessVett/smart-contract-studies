# Tools

Utilities supporting the analyses in this repository.

## `onchain_profile.py`

Builds an on-chain profile of a deployed ERC20 token — the questions a static
source review cannot answer, because they depend on what has actually happened
since deployment.

```bash
python3 tools/onchain_profile.py 0x9eAeBd7E73D97E78c77fAB743e6FFA1b550e224c
```

**No dependencies.** Standard library only: no `pip install`, no API key. It
ships its own keccak-256 (Python's `hashlib` provides SHA3, whose padding
differs from Keccak and yields the wrong selectors), so arbitrary function
signatures resolve without a crypto library.

### What it reports

| Section | Answers |
|---|---|
| Identity | supply, decimals, verification status, proxy/upgradeability |
| Supply mechanics | whether supply is elastic (rebase), and how it has moved |
| Ownership | current owner, EOA or contract, transfer history |
| Deployer & funding trail | who deployed it, and where their first ETH came from |
| Supply distribution | where the initial supply actually went |
| Top holders | concentration, with exchange and contract labels |
| Assets held by the contract | tokens and ETH sent to the contract itself |
| Recovery-function safety | whether recovery paths work against non-compliant tokens |

### Options

```
--rpc URL          JSON-RPC endpoint (default: ethereum-rpc.publicnode.com)
--explorer URL     Blockscout-compatible explorer (default: eth.blockscout.com)
--holders N        how many top holders to list (default: 10)
--skip-recovery    skip the recovery probe (~12 fewer eth_call round trips)
--json             emit raw JSON instead of the report
```

Point `--rpc` and `--explorer` at another chain's endpoints to profile tokens
outside Ethereum mainnet, provided the explorer speaks the Blockscout API.

Exit codes: `0` profile produced · `1` usage error · `2` RPC unreachable.

### The recovery probe

The most useful check, and the one that motivated the tool. Many token
contracts expose a `removeStuckToken`-style function to recover assets sent to
them by mistake. If it calls the token through an interface declaring
`returns (bool)`, it **reverts against USDT**, which returns no data from
`transfer()` — so those tokens are stranded forever. This is the class of bug
`SafeERC20` exists to prevent, and reading the source is not enough to catch
it: the function looks correct.

The probe simulates each known recovery signature twice against live chain
state — once with USDT, once with USDC as a compliant control — and reports a
function as unsafe only when it succeeds with the control and reverts with
USDT. Two details make it reliable:

- **The control run.** A missing function also reverts, so without a control
  every absent function would be flagged.
- **A zero amount.** A compliant ERC20 accepts a zero-value transfer without
  needing a balance, so the probe discriminates purely on return data — the
  actual defect — rather than on whether the contract happens to hold the
  probe token.

Because the control token is independent of the contract under test, the probe
works on any contract with a recovery function, not only on ERC20s. That
matters: an earlier version used the contract itself as the control, which
silently reported nothing for a presale, a vault or a staking contract.

Two live instances found so far, both from the same team:

| Contract | Function | Stuck |
|---|---|---|
| [RXS token](../tokens/RXS/) | `removeStuckToken` | 2,320.36 USDT |
| [Rexas Presale](../defi/RexasPresale/) | `WithdrawTokens` | 46.85 USDT |

Note the capitalisation of the second: selectors are case-sensitive, so
`WithdrawTokens` and `withdrawTokens` are different functions. Signature lists
have to cover the variants contracts actually use, not the ones the style guide
recommends.

### Elastic supply detection

`totalSupply()` is not always a fixed quantity. Rebase tokens rescale it, and
every holder's balance moves with it. Reporting that number flat is misleading:
market data for such tokens is routinely years out of date, and any
share-of-supply figure computed against a stale value is wrong by whatever the
supply has done since.

The tool looks for `LogRebase` events and a `monetaryPolicy()` getter. When it
finds them it marks the supply `<< ELASTIC` and adds a section with the rebase
count, the supply at first and latest rebase, the total growth factor, and any
long dormancy — because a five-year pause followed by a burst is a different
story from steady operation, and the reader should see it.

Running it against LEASH reports 315 rebases and a 6.4 trillion× growth factor
against a published supply figure frozen in 2020. That discrepancy is what
prompted the [LEASH study](../tokens/LEASH/).

### Two traps it handles

Both produce a confidently wrong answer if ignored, and both were hit while
building this tool:

1. **Public nodes silently truncate.** Many reject historical `eth_getLogs`
   ranges; some return an *empty list* rather than an error, which reads as
   "no events ever occurred". The tool cross-checks against the explorer and
   prefers whichever source actually found events.
2. **`Ownable` emits at construction.** The constructor fires
   `OwnershipTransferred(0x0, deployer)`, so an Ownable contract never shows
   zero events. The tool separates that initialisation from genuine
   post-deployment transfers, and reports them differently.

### Verifying the keccak implementation

The hash function is the tool's single point of total failure — wrong
selectors would make every contract read silently meaningless rather than
error out. Check it against known vectors:

```bash
cd tools
python3 -c "
from onchain_profile import keccak256, selector
assert keccak256(b'').hex() == 'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470'
assert keccak256(b'abc').hex() == '4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45'
assert selector('owner()') == '0x8da5cb5b'
assert selector('transfer(address,uint256)') == '0xa9059cbb'
assert selector('balanceOf(address)') == '0x70a08231'
print('keccak-256 OK')
"
```

### Limitations

- Explorer endpoints paginate at 10,000 records; aggregates over very active
  addresses are lower bounds, not totals.
- Holder data and address labels come from the explorer, not from chain state
  directly — they are as current and as complete as that index.
- The recovery probe covers the signatures in `RECOVERY_SIGNATURES`. A contract
  using a different name will not be probed; add it to that list.
- Centralised-exchange order books are not on-chain and are outside scope.

## Contributing a tool

Tools should run from a clean checkout with no install step where possible,
state their limitations in `--help` and in this file, and fail loudly rather
than return a plausible wrong answer. See [CONTRIBUTING.md](../CONTRIBUTING.md).

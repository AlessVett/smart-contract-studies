# Smart Contract Studies

A comprehensive repository for analyzing and studying various smart contracts across different blockchain ecosystems.

## Available Studies

| Study | Network | Address | Contents |
|---|---|---|---|
| [Rexas Finance (RXS)](tokens/RXS/) | Ethereum | [`0x9eAeBd7E…550e224c`](https://etherscan.io/address/0x9eaebd7e73d97e78c77fab743e6ffa1b550e224c) | Static code analysis + on-chain forensic analysis |

## Repository Structure

Studies are filed by category. Only `tokens/` is populated so far; the
remaining directories are the planned taxonomy and are created as studies
are added.

```
smart-contract-studies/
├── tokens/         # ERC20, ERC721, and other token standards  [populated]
├── tools/          # Analysis utilities  [populated]
├── defi/           # DeFi protocols (AMMs, lending, yield farming)  [planned]
├── nft/            # NFT contracts and marketplaces  [planned]
└── dao/            # DAO and governance contracts  [planned]
```

## Tools

| Tool | Purpose |
|---|---|
| [`onchain_profile.py`](tools/onchain_profile.py) | Profiles a deployed ERC20: ownership, deployer funding trail, supply distribution, holder concentration, and recovery-function safety. No dependencies. |

```bash
python3 tools/onchain_profile.py 0x9eAeBd7E73D97E78c77fAB743e6FFA1b550e224c
```

See [tools/README.md](tools/README.md) for options and caveats.

Each study directory follows the layout described in
[CONTRIBUTING.md](CONTRIBUTING.md#file-structure).

## How to Use This Repository

Each contract study includes:
- Original contract source code (.sol files), verified against the deployed bytecode
- Detailed analysis and documentation
- Security considerations, with findings rated by severity
- Gas optimization notes
- Potential vulnerabilities and recommendations

Where a study also covers deployed behaviour, an on-chain analysis
document accompanies the static one: the first describes what the code
*can* do, the second what *actually happened*.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for
analysis standards, file layout, and the submission process, and
[CONTRIBUTORS.md](CONTRIBUTORS.md) for those who have contributed.

## Disclaimer

These studies are for educational purposes only. Always conduct your own research and security audits before interacting with any smart contract.
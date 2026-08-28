#!/usr/bin/env python3
"""
onchain_profile.py — build an on-chain profile of a deployed ERC20 token.

Answers the questions a static source review cannot: who actually owns the
contract right now, where the deployer's funding came from, how the supply
was really distributed, and whether the contract's recovery functions work
against non-compliant tokens.

Written for the smart-contract-studies repository. Standard library only —
no pip install, no API key. Ships its own keccak-256 so arbitrary function
signatures can be resolved without a crypto dependency.

Usage:
    python3 onchain_profile.py 0x9eAeBd7E73D97E78c77fAB743e6FFA1b550e224c
    python3 onchain_profile.py <address> --json > profile.json
    python3 onchain_profile.py <address> --rpc https://my-node --skip-recovery

Exit codes: 0 profile produced · 1 usage error · 2 network/RPC failure
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

DEFAULT_RPC = "https://ethereum-rpc.publicnode.com"
DEFAULT_EXPLORER = "https://eth.blockscout.com"
TIMEOUT = 45
UA = "smart-contract-studies/onchain_profile"

# Well-known mainnet addresses used as probes and reference points.
USDT = "0xdAC17F958D2ee523a2206206994597C13D831ec7"  # returns no data from transfer()
ZERO = "0x0000000000000000000000000000000000000000"

# keccak256("Transfer(address,address,uint256)")
TOPIC_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
# keccak256("OwnershipTransferred(address,address)")
TOPIC_OWNERSHIP = "0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0"


# --------------------------------------------------------------------------
# keccak-256, stdlib only.
# Needed to derive selectors for arbitrary signatures; hashlib ships SHA3,
# which uses different padding and will not produce Ethereum selectors.
# --------------------------------------------------------------------------

_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
_ROT = [
    [0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56], [27, 20, 39, 8, 14],
]
_MASK = (1 << 64) - 1


def _rotl(x, n):
    return ((x << n) | (x >> (64 - n))) & _MASK


def _keccak_f(a):
    for rnd in range(24):
        c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rotl(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                a[x][y] ^= d[x]
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                b[y][(2 * x + 3 * y) % 5] = _rotl(a[x][y], _ROT[x][y])
        for x in range(5):
            for y in range(5):
                a[x][y] = b[x][y] ^ ((~b[(x + 1) % 5][y]) & _MASK) & b[(x + 2) % 5][y]
        a[0][0] ^= _RC[rnd]
    return a


def keccak256(data: bytes) -> bytes:
    rate = 136  # 1088 bits, the rate for keccak-256
    padded = bytearray(data)
    padded.append(0x01)  # Keccak padding, not SHA3's 0x06
    while len(padded) % rate != 0:
        padded.append(0x00)
    padded[-1] |= 0x80

    state = [[0] * 5 for _ in range(5)]
    for off in range(0, len(padded), rate):
        block = padded[off:off + rate]
        for i in range(rate // 8):
            lane = int.from_bytes(block[i * 8:(i + 1) * 8], "little")
            state[i % 5][i // 5] ^= lane
        state = _keccak_f(state)

    out = bytearray()
    for i in range(4):  # 32 bytes
        out += state[i % 5][i // 5].to_bytes(8, "little")
    return bytes(out[:32])


def selector(signature: str) -> str:
    """'owner()' -> '0x8da5cb5b'"""
    return "0x" + keccak256(signature.encode()).hex()[:8]


# --------------------------------------------------------------------------
# Chain access
# --------------------------------------------------------------------------

class ChainError(Exception):
    pass


class Chain:
    def __init__(self, rpc: str, explorer: str):
        self.rpc = rpc.rstrip("/")
        self.explorer = explorer.rstrip("/")
        self._id = 0

    def _http(self, url, payload=None):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        body = None
        if payload is not None:
            body = json.dumps(payload).encode()
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, data=body, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise ChainError(f"HTTP {e.code} for {url}")
        except Exception as e:  # noqa: BLE001 - surface anything as a chain error
            raise ChainError(f"{type(e).__name__}: {e}")

    def rpc_call(self, method, params):
        self._id += 1
        res = self._http(self.rpc, {"jsonrpc": "2.0", "id": self._id,
                                    "method": method, "params": params})
        if "error" in res:
            raise ChainError(res["error"].get("message", "rpc error"))
        return res.get("result")

    def eth_call(self, to, data, frm=None):
        """Returns hex result, or None if the call reverts."""
        tx = {"to": to, "data": data}
        if frm:
            tx["from"] = frm
        try:
            return self.rpc_call("eth_call", [tx, "latest"])
        except ChainError:
            return None

    def api(self, path):
        return self._http(f"{self.explorer}{path}")


# --------------------------------------------------------------------------
# ABI decoding helpers (only the shapes this tool needs)
# --------------------------------------------------------------------------

def dec_uint(hexstr):
    if not hexstr or hexstr == "0x":
        return None
    return int(hexstr, 16)


def dec_addr(hexstr):
    if not hexstr or len(hexstr) < 66:
        return None
    return "0x" + hexstr[-40:]


def dec_string(hexstr):
    """Decodes both dynamic string returns and bytes32-style names."""
    if not hexstr or hexstr == "0x":
        return None
    raw = bytes.fromhex(hexstr[2:])
    if len(raw) >= 64:
        try:
            length = int.from_bytes(raw[32:64], "big")
            if 0 < length <= len(raw) - 64:
                return raw[64:64 + length].decode("utf-8", "replace")
        except Exception:
            pass
    return raw.rstrip(b"\x00").decode("utf-8", "replace") or None


def units(value, decimals):
    return value / (10 ** decimals) if value is not None and decimals else value


def tags_of(obj):
    meta = (obj or {}).get("metadata") or {}
    return [t.get("name") for t in meta.get("tags", []) if t.get("name")]


def short(addr):
    return f"{addr[:10]}…{addr[-6:]}" if addr and len(addr) > 20 else addr


# --------------------------------------------------------------------------
# Profile sections
# --------------------------------------------------------------------------

def section_identity(chain, addr):
    out = {}
    out["name"] = dec_string(chain.eth_call(addr, selector("name()")))
    out["symbol"] = dec_string(chain.eth_call(addr, selector("symbol()")))
    dec = dec_uint(chain.eth_call(addr, selector("decimals()")))
    out["decimals"] = dec if dec is not None else 18
    out["total_supply"] = dec_uint(chain.eth_call(addr, selector("totalSupply()")))

    try:
        meta = chain.api(f"/api/v2/addresses/{addr}")
        out["is_contract"] = meta.get("is_contract")
        out["is_verified"] = meta.get("is_verified")
        out["proxy_type"] = meta.get("proxy_type")
        out["implementations"] = [i.get("address_hash") for i in meta.get("implementations") or []]
        out["creator"] = meta.get("creator_address_hash")
        out["creation_tx"] = (meta.get("creation_transaction_hash")
                              or meta.get("creation_tx_hash"))
        out["tags"] = tags_of(meta)
    except ChainError as e:
        out["explorer_error"] = str(e)
    return out


def _usable_topics(log):
    """Explorers pad `topics` to a fixed length with nulls, so a length check
    alone is not enough — the indexed slots themselves may be None."""
    topics = log.get("topics") or []
    return len(topics) >= 3 and bool(topics[1]) and bool(topics[2])


def section_ownership(chain, addr, creator):
    out = {}
    owner = dec_addr(chain.eth_call(addr, selector("owner()")))
    out["owner"] = owner
    out["has_owner_function"] = owner is not None

    if owner:
        out["renounced"] = owner.lower() == ZERO
        out["owner_is_deployer"] = bool(creator) and owner.lower() == creator.lower()
        try:
            meta = chain.api(f"/api/v2/addresses/{owner}")
            out["owner_is_contract"] = meta.get("is_contract")
            out["owner_tags"] = tags_of(meta)
            out["owner_eth"] = units(int(meta.get("coin_balance") or 0), 18)
        except ChainError:
            pass

    # Ownership history.
    #
    # Two traps here, both of which produce a confidently wrong answer:
    #
    # 1. Many public nodes reject historical ranges. Some return an error,
    #    but some return an EMPTY LIST, which reads as "never transferred".
    #    So we cross-check against the explorer and prefer whichever source
    #    actually found events.
    # 2. Ownable's constructor emits OwnershipTransferred(0x0, deployer) at
    #    deployment. Counting raw events therefore never yields zero for an
    #    Ownable contract. That initialisation event must be separated from
    #    genuine post-deployment transfers.
    events, err = [], None
    try:
        logs = chain.rpc_call("eth_getLogs", [{
            "address": addr, "topics": [TOPIC_OWNERSHIP],
            "fromBlock": "0x0", "toBlock": "latest",
        }])
        events = [{"block": int(l["blockNumber"], 16),
                   "from": "0x" + l["topics"][1][-40:],
                   "to": "0x" + l["topics"][2][-40:]}
                  for l in logs if _usable_topics(l)]
    except ChainError as e:
        err = str(e)

    if not events:  # RPC refused, or refused silently — ask the explorer
        try:
            data = chain.api(
                f"/api?module=logs&action=getLogs&fromBlock=0&toBlock=latest"
                f"&address={addr}&topic0={TOPIC_OWNERSHIP}")
            result = data.get("result")
            if isinstance(result, list):
                events = [{"block": int(l["blockNumber"], 16),
                           "from": "0x" + l["topics"][1][-40:],
                           "to": "0x" + l["topics"][2][-40:]}
                          for l in result if _usable_topics(l)]
                err = None
        except ChainError as e:
            err = err or str(e)

    if err and not events:
        out["ownership_events_error"] = err
    else:
        out["ownership_events"] = events
        out["initialisation_event"] = next(
            (e for e in events if e["from"].lower() == ZERO), None)
        out["real_transfers"] = [e for e in events if e["from"].lower() != ZERO]
    return out


def section_deployer(chain, creator):
    """Traces the deployer's first inbound transfer — often a CEX withdrawal,
    which is the only realistic attribution vector for an anonymous team."""
    if not creator:
        return {}
    out = {"address": creator}
    try:
        meta = chain.api(f"/api/v2/addresses/{creator}")
        out["is_contract"] = meta.get("is_contract")
        out["tags"] = tags_of(meta)
        out["eth_balance"] = units(int(meta.get("coin_balance") or 0), 18)

        txs = chain.api(f"/api/v2/addresses/{creator}/transactions?filter=to")
        items = txs.get("items") or []
        funders = []
        for t in reversed(items):  # oldest first
            value = int(t.get("value") or 0)
            if value <= 0:
                continue
            frm = t.get("from") or {}
            funders.append({
                "timestamp": t.get("timestamp"),
                "from": frm.get("hash"),
                "tags": tags_of(frm),
                "eth": units(value, 18),
            })
        out["funding"] = funders[:5]
        out["funded_by_exchange"] = [
            f for f in funders
            if any("exchange" in t.lower() or "hot wallet" in t.lower() for t in f["tags"])
        ][:3]
    except ChainError as e:
        out["error"] = str(e)
    return out


def section_distribution(chain, token, creator, decimals):
    """Where the initial supply actually went."""
    if not creator:
        return {}
    out = {}
    try:
        data = chain.api(
            f"/api/v2/addresses/{creator}/token-transfers?token={token}")
        moves = []
        for t in data.get("items") or []:
            frm = ((t.get("from") or {}).get("hash") or "").lower()
            if frm != creator.lower():
                continue
            to = t.get("to") or {}
            raw = int(((t.get("total") or {}).get("value")) or 0)
            moves.append({
                "timestamp": (t.get("timestamp") or "")[:10],
                "to": to.get("hash"),
                "tags": tags_of(to),
                "amount": units(raw, decimals),
            })
        moves.sort(key=lambda m: m["amount"], reverse=True)
        out["transfers_from_deployer"] = moves
        out["total_distributed"] = sum(m["amount"] for m in moves)
    except ChainError as e:
        out["error"] = str(e)
    return out


def section_holders(chain, token, decimals, supply, limit):
    out = {}
    try:
        data = chain.api(f"/api/v2/tokens/{token}/holders")
        rows = []
        for h in (data.get("items") or [])[:limit]:
            a = h.get("address") or {}
            amount = units(int(h.get("value") or 0), decimals)
            rows.append({
                "address": a.get("hash"),
                "is_contract": a.get("is_contract"),
                "tags": tags_of(a),
                "amount": amount,
                "pct": (amount / units(supply, decimals) * 100) if supply else None,
            })
        out["top_holders"] = rows
        out["concentration_top10"] = sum(r["pct"] or 0 for r in rows[:10])
    except ChainError as e:
        out["error"] = str(e)
    return out


def section_stuck_assets(chain, token, decimals):
    """Assets sitting in the token contract itself — usually sent by mistake,
    and only retrievable if the contract exposes a working recovery path."""
    out = {}
    try:
        meta = chain.api(f"/api/v2/addresses/{token}")
        out["eth"] = units(int(meta.get("coin_balance") or 0), 18)
    except ChainError:
        pass
    try:
        balances = chain.api(f"/api/v2/addresses/{token}/token-balances")
        rows = []
        for b in balances or []:
            ti = b.get("token") or {}
            d = int(ti.get("decimals") or 0)
            amount = units(int(b.get("value") or 0), d) if d else int(b.get("value") or 0)
            if not amount or amount < 0.000001:
                continue
            rows.append({"symbol": ti.get("symbol"), "address": ti.get("address_hash"),
                         "amount": amount})
        rows.sort(key=lambda r: r["amount"], reverse=True)
        out["tokens"] = rows[:15]
    except ChainError as e:
        out["error"] = str(e)
    return out


RECOVERY_SIGNATURES = [
    "removeStuckToken(address,address,uint256)",
    "withdrawStuckToken(address,address,uint256)",
    "rescueToken(address,address,uint256)",
    "recoverERC20(address,uint256)",
    "withdrawToken(address,uint256)",
    "clearStuckToken(address,uint256)",
]


def section_recovery(chain, token, owner):
    """Probes recovery functions against a non-compliant token.

    USDT's transfer() returns no data. A recovery function calling it through
    an interface declaring `returns (bool)` reverts under Solidity 0.8, making
    any USDT sent to the contract permanently unrecoverable. This is the class
    of bug SafeERC20 exists to prevent, and it is invisible to source reading
    alone — it only shows up when you simulate the call.
    """
    out = {"probed": [], "note": None}
    if not owner or owner.lower() == ZERO:
        out["note"] = "no owner to simulate from; recovery probe skipped"
        return out

    recipient = owner
    for sig in RECOVERY_SIGNATURES:
        sel = selector(sig)
        arg_count = sig.count(",") + 1
        # Encode: (token, recipient, amount) or (token, amount)
        if arg_count == 3:
            data = (sel
                    + USDT[2:].rjust(64, "0").lower()
                    + recipient[2:].rjust(64, "0").lower()
                    + f"{1:064x}")
        else:
            data = sel + USDT[2:].rjust(64, "0").lower() + f"{1:064x}"

        res = chain.eth_call(token, data, frm=owner)
        # A missing function also reverts, so distinguish via the compliant
        # control probe below rather than treating every revert as the bug.
        out["probed"].append({"signature": sig, "reverts_with_usdt": res is None})

    # Control: does any probed function exist at all? Use the token itself,
    # which is ERC20-compliant by construction.
    for entry in out["probed"]:
        sig = entry["signature"]
        sel = selector(sig)
        arg_count = sig.count(",") + 1
        if arg_count == 3:
            data = (sel + token[2:].rjust(64, "0").lower()
                    + recipient[2:].rjust(64, "0").lower() + f"{1:064x}")
        else:
            data = sel + token[2:].rjust(64, "0").lower() + f"{1:064x}"
        entry["succeeds_with_compliant_token"] = chain.eth_call(token, data, frm=owner) is not None

    vulnerable = [e for e in out["probed"]
                  if e["succeeds_with_compliant_token"] and e["reverts_with_usdt"]]
    out["unsafe_recovery_functions"] = [e["signature"] for e in vulnerable]
    out["present_recovery_functions"] = [e["signature"] for e in out["probed"]
                                         if e["succeeds_with_compliant_token"]]
    return out


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def hr(title):
    print(f"\n{'─' * 72}\n{title}\n{'─' * 72}")


def render(p):
    idn, own = p["identity"], p["ownership"]
    dec = idn.get("decimals") or 18
    supply = units(idn.get("total_supply"), dec)

    print(f"\n  {idn.get('name') or '?'} ({idn.get('symbol') or '?'})")
    print(f"  {p['address']}")

    hr("IDENTITY")
    print(f"  total supply   : {supply:,.0f}" if supply else "  total supply   : n/d")
    print(f"  decimals       : {dec}")
    print(f"  verified       : {idn.get('is_verified')}")
    proxy = idn.get("proxy_type")
    print(f"  proxy          : {proxy or 'no — bytecode immutable'}")
    if idn.get("implementations"):
        print(f"  implementation : {', '.join(idn['implementations'])}")
    if idn.get("tags"):
        print(f"  labels         : {', '.join(idn['tags'])}")

    hr("OWNERSHIP")
    if not own.get("has_owner_function"):
        print("  no owner() function — contract is not Ownable")
    else:
        o = own.get("owner")
        print(f"  owner          : {o}")
        if own.get("renounced"):
            print("  status         : RENOUNCED (zero address)")
        else:
            kind = "contract (multisig/timelock?)" if own.get("owner_is_contract") else "EOA — single private key"
            print(f"  account type   : {kind}")
            if own.get("owner_is_deployer"):
                print("  note           : owner is the original deployer")
            if own.get("owner_tags"):
                print(f"  labels         : {', '.join(own['owner_tags'])}")
        evs = own.get("ownership_events")
        if evs is None:
            print(f"  history        : unavailable ({own.get('ownership_events_error', 'n/d')})")
        else:
            init = own.get("initialisation_event")
            real = own.get("real_transfers") or []
            if init:
                print(f"  initialised    : block {init['block']} (constructor, 0x0 → deployer)")
            if not real:
                print("  history        : never transferred after deployment")
            else:
                print(f"  history        : {len(real)} transfer(s) after deployment")
                for e in real[-4:]:
                    print(f"                   block {e['block']}: {short(e['from'])} → {short(e['to'])}")

    dep = p.get("deployer") or {}
    if dep.get("address"):
        hr("DEPLOYER & FUNDING TRAIL")
        print(f"  deployer       : {dep['address']}")
        if dep.get("tags"):
            print(f"  labels         : {', '.join(dep['tags'])}")
        for f in dep.get("funding", [])[:3]:
            tag = f" [{', '.join(f['tags'])}]" if f["tags"] else ""
            print(f"  funded         : {(f['timestamp'] or '')[:19]}  {f['eth']:.4f} ETH")
            print(f"                   from {f['from']}{tag}")
        if dep.get("funded_by_exchange"):
            print("\n  ATTRIBUTION: deployer was funded from a centralised exchange.")
            print("  Exchanges enforce KYC on withdrawals, so a verified identity exists")
            print("  there. It is reachable only through formal legal process.")

    dist = p.get("distribution") or {}
    if dist.get("transfers_from_deployer"):
        hr("SUPPLY DISTRIBUTION FROM DEPLOYER")
        for m in dist["transfers_from_deployer"][:12]:
            pct = (m["amount"] / supply * 100) if supply else 0
            tag = f" [{', '.join(m['tags'])}]" if m["tags"] else ""
            print(f"  {m['timestamp']}  {m['amount']:>18,.0f}  ({pct:5.2f}%)  → {m['to']}{tag}")
        tot = dist.get("total_distributed") or 0
        print(f"  {'':10}  {tot:>18,.0f}  ({(tot / supply * 100) if supply else 0:5.2f}%)  distributed")
        if supply:
            print(f"  {'':10}  {supply - tot:>18,.0f}  ({(supply - tot) / supply * 100:5.2f}%)  retained by deployer")

    hold = p.get("holders") or {}
    if hold.get("top_holders"):
        hr("TOP HOLDERS")
        for h in hold["top_holders"]:
            kind = "contract" if h["is_contract"] else "EOA"
            tag = f" [{', '.join(h['tags'])}]" if h["tags"] else ""
            print(f"  {h['pct'] or 0:5.2f}%  {h['amount']:>18,.0f}  {h['address']}  {kind}{tag}")
        print(f"\n  top-10 concentration: {hold.get('concentration_top10', 0):.2f}%")

    stuck = p.get("stuck_assets") or {}
    if stuck.get("eth") or stuck.get("tokens"):
        hr("ASSETS HELD BY THE CONTRACT")
        if stuck.get("eth"):
            print(f"  {stuck['eth']:>18,.6f}  ETH")
        for t in (stuck.get("tokens") or [])[:10]:
            print(f"  {t['amount']:>18,.4f}  {t['symbol'] or '?'}")
        print("\n  Assets sent to a token contract are retrievable only through a")
        print("  working recovery function — see the next section.")

    rec = p.get("recovery") or {}
    if rec.get("present_recovery_functions") or rec.get("note"):
        hr("RECOVERY-FUNCTION SAFETY")
        if rec.get("note"):
            print(f"  {rec['note']}")
        for sig in rec.get("present_recovery_functions", []):
            unsafe = sig in rec.get("unsafe_recovery_functions", [])
            mark = "UNSAFE" if unsafe else "ok"
            print(f"  [{mark:>6}]  {sig}")
        if rec.get("unsafe_recovery_functions"):
            print("\n  FINDING: the recovery path reverts against USDT, which returns no")
            print("  data from transfer(). Non-compliant tokens sent to this contract")
            print("  are permanently unrecoverable. Remedy: OpenZeppelin SafeERC20.")
            usdt_held = [t for t in (stuck.get("tokens") or [])
                         if (t.get("symbol") or "").upper() == "USDT"]
            if usdt_held:
                print(f"  ALREADY MATERIALISED: {usdt_held[0]['amount']:,.2f} USDT stuck.")
        elif rec.get("present_recovery_functions"):
            print("\n  Recovery functions handle non-compliant tokens correctly.")

    print()


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Build an on-chain profile of a deployed ERC20 token.",
        epilog="Example: python3 onchain_profile.py "
               "0x9eAeBd7E73D97E78c77fAB743e6FFA1b550e224c")
    ap.add_argument("address", help="token contract address (0x…)")
    ap.add_argument("--rpc", default=DEFAULT_RPC, help=f"JSON-RPC endpoint (default: {DEFAULT_RPC})")
    ap.add_argument("--explorer", default=DEFAULT_EXPLORER,
                    help=f"Blockscout-compatible explorer (default: {DEFAULT_EXPLORER})")
    ap.add_argument("--holders", type=int, default=10, help="how many top holders to list")
    ap.add_argument("--skip-recovery", action="store_true",
                    help="skip the recovery-function probe (saves ~12 eth_call round trips)")
    ap.add_argument("--json", action="store_true", help="emit raw JSON instead of a report")
    args = ap.parse_args()

    addr = args.address.strip()
    if not (addr.startswith("0x") and len(addr) == 42):
        print(f"error: '{addr}' is not a 20-byte address", file=sys.stderr)
        return 1

    chain = Chain(args.rpc, args.explorer)

    # Fail fast and clearly if the endpoint is unusable.
    try:
        chain.rpc_call("eth_blockNumber", [])
    except ChainError as e:
        print(f"error: RPC endpoint unreachable ({e})", file=sys.stderr)
        return 2

    profile = {"address": addr, "rpc": args.rpc, "explorer": args.explorer}
    profile["identity"] = section_identity(chain, addr)

    if profile["identity"].get("is_contract") is False:
        print(f"error: {addr} is an EOA, not a contract", file=sys.stderr)
        return 1

    creator = profile["identity"].get("creator")
    dec = profile["identity"].get("decimals") or 18

    profile["ownership"] = section_ownership(chain, addr, creator)
    profile["deployer"] = section_deployer(chain, creator)
    profile["distribution"] = section_distribution(chain, addr, creator, dec)
    profile["holders"] = section_holders(chain, addr, dec,
                                         profile["identity"].get("total_supply"),
                                         args.holders)
    profile["stuck_assets"] = section_stuck_assets(chain, addr, dec)
    profile["recovery"] = ({} if args.skip_recovery
                           else section_recovery(chain, addr,
                                                 profile["ownership"].get("owner")))

    if args.json:
        print(json.dumps(profile, indent=2, default=str))
    else:
        render(profile)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)

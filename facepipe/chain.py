"""Stage 7-8: anchor a verified match on Base Sepolia, and verify it later.

Two ideas carry the "tamper-evident" claim:

  1. The record is serialised to *canonical* JSON (sorted keys, no incidental
     whitespace) before hashing. Without that, re-serialising the same data
     could produce a different hash and the integrity check would be worthless.
  2. Only the 32-byte hash goes into storage. The readable payload rides in the
     event, which is roughly an order of magnitude cheaper in gas and is what a
     block explorer decodes for a human reader.

Targets web3 8.x. Snippets written for 6.x will not run here - notably
`signed.raw_transaction`, which was `rawTransaction` in older versions.
"""

import json
import os
from pathlib import Path

from eth_account import Account
from web3 import Web3

from . import config

SOLC_VERSION = "0.8.24"
CONTRACT_PATH = config.ROOT / "contracts" / "FaceMatchRegistry.sol"
BUILD_PATH = config.ROOT / "out" / "FaceMatchRegistry.build.json"
EXPLORER = "https://sepolia.basescan.org"


# --- compilation -----------------------------------------------------------

def compile_contract(force: bool = False) -> dict:
    """Compile the contract, caching the artifact. Returns {abi, bytecode}."""
    if BUILD_PATH.exists() and not force:
        return json.loads(BUILD_PATH.read_text(encoding="utf-8"))

    import solcx

    installed = [str(v) for v in solcx.get_installed_solc_versions()]
    if SOLC_VERSION not in installed:
        print(f"      installing solc {SOLC_VERSION} (one time)")
        solcx.install_solc(SOLC_VERSION)

    compiled = solcx.compile_source(
        CONTRACT_PATH.read_text(encoding="utf-8"),
        output_values=["abi", "bin"],
        solc_version=SOLC_VERSION,
        optimize=True,
        optimize_runs=200,
    )
    key = next(k for k in compiled if k.endswith(":FaceMatchRegistry"))
    artifact = {"abi": compiled[key]["abi"], "bytecode": compiled[key]["bin"]}
    BUILD_PATH.parent.mkdir(parents=True, exist_ok=True)
    BUILD_PATH.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return artifact


# --- connection ------------------------------------------------------------

def get_w3() -> Web3:
    rpc = os.getenv("BASE_SEPOLIA_RPC", "https://sepolia.base.org")
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 60}))
    if not w3.is_connected():
        raise SystemExit(f"Cannot reach the Base Sepolia RPC at {rpc}")
    return w3


def get_account():
    key = os.getenv("DEPLOYER_PRIVATE_KEY", "").strip()
    if not key:
        raise SystemExit(
            "DEPLOYER_PRIVATE_KEY missing from .env - run scripts/day2_wallet.py"
        )
    return Account.from_key(key if key.startswith("0x") else "0x" + key)


def _send(w3, acct, tx):
    """Sign, send, and wait. Returns the receipt."""
    tx.setdefault("nonce", w3.eth.get_transaction_count(acct.address))
    tx.setdefault("chainId", w3.eth.chain_id)
    tx.setdefault("gasPrice", w3.eth.gas_price)
    if "gas" not in tx:
        tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.25)
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)


def _hex(value) -> str:
    """web3 8.x returns HexBytes; normalise to a 0x-prefixed string."""
    text = value.hex() if hasattr(value, "hex") else str(value)
    return text if text.startswith("0x") else "0x" + text


# --- deploy ----------------------------------------------------------------

def deploy(log=print) -> str:
    w3, acct = get_w3(), get_account()
    balance = w3.eth.get_balance(acct.address)
    log(f"      deployer {acct.address}")
    log(f"      balance  {w3.from_wei(balance, 'ether')} ETH")
    if balance == 0:
        raise SystemExit(
            "Deployer has no ETH. Fund it from a Base Sepolia faucet first."
        )

    artifact = compile_contract()
    contract = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
    tx = contract.constructor().build_transaction(
        {"from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address)}
    )
    receipt = _send(w3, acct, tx)
    if receipt.status != 1:
        raise SystemExit(f"Deployment reverted: {receipt}")
    log(f"      deployed at {receipt.contractAddress}")
    log(f"      {EXPLORER}/address/{receipt.contractAddress}")
    return receipt.contractAddress


# --- the record ------------------------------------------------------------

def canonical_json(record: dict) -> bytes:
    """Deterministic serialisation - the whole integrity claim rests on this."""
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def record_hash(record: dict) -> bytes:
    return Web3.keccak(canonical_json(record))


def build_record(probe_result: dict, match: dict) -> dict:
    """The canonical off-chain record for one verified match."""
    return {
        "version": 1,
        "query_image_sha256": probe_result["image_sha256"],
        "query_embedding_sha256": probe_result["query_embedding_sha256"],
        "hosted_url": probe_result["hosted_url"],
        "match_url": match["link"],
        "match_platform": match["source"],
        "match_title": match.get("title", ""),
        "match_thumbnail": match["thumbnail"],
        "similarity": match["score"],
        "threshold": probe_result["threshold"],
        "engine": "google_lens/serpapi",
    }


def anchor(record: dict, contract_address: str = None, log=print) -> dict:
    """Write one record on-chain. Returns tx details."""
    w3, acct = get_w3(), get_account()
    address = contract_address or os.getenv("CONTRACT_ADDRESS", "").strip()
    if not address:
        raise SystemExit("CONTRACT_ADDRESS missing - run scripts/day2_deploy.py")

    artifact = compile_contract()
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(address), abi=artifact["abi"]
    )

    rhash = record_hash(record)
    # Similarity is clamped, not wrapped: a negative cosine means "not this
    # person" and would otherwise underflow into a huge positive score.
    sim_bps = max(0, min(10000, round(record["similarity"] * 10000)))
    thr_bps = max(0, min(10000, round(record["threshold"] * 10000)))

    log(f"      record hash  {_hex(rhash)}")
    log(f"      similarity   {sim_bps} bps (threshold {thr_bps})")

    if contract.functions.isRecorded(rhash).call():
        log("      already anchored on-chain - skipping duplicate write")
        return {"record_hash": _hex(rhash), "duplicate": True}

    tx = contract.functions.recordMatch(
        rhash,
        record["match_url"],
        record["match_platform"],
        sim_bps,
        thr_bps,
        bytes.fromhex(record["query_image_sha256"]),
        bytes.fromhex(record["query_embedding_sha256"]),
    ).build_transaction(
        {"from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address)}
    )
    receipt = _send(w3, acct, tx)
    if receipt.status != 1:
        raise SystemExit(f"recordMatch reverted: {receipt}")

    tx_hex = _hex(receipt.transactionHash)
    log(f"      block {receipt.blockNumber}, gas used {receipt.gasUsed}")
    log(f"      {EXPLORER}/tx/{tx_hex}")
    return {
        "record_hash": _hex(rhash),
        "tx_hash": tx_hex,
        "block": receipt.blockNumber,
        "gas_used": receipt.gasUsed,
        "contract": address,
        "explorer": f"{EXPLORER}/tx/{tx_hex}",
        "duplicate": False,
    }


def verify(record_path, contract_address: str = None, log=print) -> bool:
    """Re-hash a local record and assert the chain agrees. The tamper check."""
    record = json.loads(Path(record_path).read_text(encoding="utf-8"))
    rhash = record_hash(record)
    log(f"      local re-hash {_hex(rhash)}")

    w3 = get_w3()
    address = contract_address or os.getenv("CONTRACT_ADDRESS", "").strip()
    if not address:
        raise SystemExit("CONTRACT_ADDRESS missing from .env")
    artifact = compile_contract()
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(address), abi=artifact["abi"]
    )
    ts, submitter = contract.functions.records(rhash).call()
    if ts == 0:
        log("      NOT FOUND on-chain - the local record does not match what was")
        log("      anchored. Either it was altered, or it was never recorded.")
        return False
    log(f"      anchored at unix {ts} by {submitter}")
    log("      MATCH - the local record is byte-identical to what was anchored.")
    return True

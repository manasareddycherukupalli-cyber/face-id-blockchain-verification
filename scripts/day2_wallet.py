"""Day 2, step 1: create the deployer wallet and print the address to fund.

Generates a fresh keypair and writes the private key into .env (which is
gitignored). Refuses to overwrite an existing key - losing the key that owns
your deployed contract mid-project would cost you a redeploy you do not have
time for.

This is a throwaway testnet key. Never fund it with real money.

    python scripts/day2_wallet.py
"""

import _bootstrap  # noqa: F401

import os
import secrets
from pathlib import Path

from eth_account import Account

from facepipe import config

FAUCETS = [
    ("Coinbase CDP", "https://portal.cdp.coinbase.com/products/faucet"),
    ("Alchemy", "https://www.alchemy.com/faucets/base-sepolia"),
    ("QuickNode", "https://faucet.quicknode.com/base/sepolia"),
]


def main() -> int:
    env_path = config.ROOT / ".env"
    existing = os.getenv("DEPLOYER_PRIVATE_KEY", "").strip()

    if existing:
        acct = Account.from_key(
            existing if existing.startswith("0x") else "0x" + existing
        )
        print("A deployer key already exists in .env - keeping it.")
        print(f"\n  address: {acct.address}\n")
        print("Delete the DEPLOYER_PRIVATE_KEY line yourself if you really want")
        print("a new one, but note the old contract stays owned by the old key.")
        return 0

    priv = "0x" + secrets.token_hex(32)
    acct = Account.from_key(priv)

    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    if "DEPLOYER_PRIVATE_KEY=" in text:
        text = text.replace("DEPLOYER_PRIVATE_KEY=\n", f"DEPLOYER_PRIVATE_KEY={priv}\n")
    else:
        text += f"\nDEPLOYER_PRIVATE_KEY={priv}\n"
    env_path.write_text(text, encoding="utf-8")

    print("New Base Sepolia deployer wallet created and saved to .env")
    print(f"\n  address: {acct.address}\n")
    print("Fund it with testnet ETH - you need only a tiny amount:")
    for name, url in FAUCETS:
        print(f"  {name:<14} {url}")
    print("\nSome faucets require a mainnet ETH balance on the same address.")
    print("If one refuses you, try the next rather than giving up.")
    print("\nThis is a throwaway testnet key. Never send real funds to it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

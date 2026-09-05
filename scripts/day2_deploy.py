"""Day 2, step 2: compile and deploy FaceMatchRegistry to Base Sepolia.

Writes CONTRACT_ADDRESS back into .env so the pipeline picks it up.

    python scripts/day2_deploy.py            # compile + deploy
    python scripts/day2_deploy.py --compile-only   # no ETH needed
"""

import _bootstrap  # noqa: F401

import argparse

from facepipe import chain, config


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compile-only", action="store_true",
                    help="compile without deploying (needs no testnet ETH)")
    args = ap.parse_args()

    print("[1/2] compiling contract")
    artifact = chain.compile_contract(force=True)
    size = len(artifact["bytecode"]) // 2
    fns = [e["name"] for e in artifact["abi"] if e.get("type") == "function"]
    evs = [e["name"] for e in artifact["abi"] if e.get("type") == "event"]
    print(f"      solc {chain.SOLC_VERSION}, {size} bytes of bytecode")
    print(f"      functions: {', '.join(fns)}")
    print(f"      events:    {', '.join(evs)}")
    if size > 24576:
        print("      WARNING: over the 24KB EIP-170 limit - will not deploy")

    if args.compile_only:
        print("\ncompile-only: stopping before deployment.")
        return 0

    print("[2/2] deploying to Base Sepolia")
    address = chain.deploy()

    env_path = config.ROOT / ".env"
    text = env_path.read_text(encoding="utf-8")
    if "CONTRACT_ADDRESS=" in text:
        import re
        text = re.sub(r"CONTRACT_ADDRESS=.*", f"CONTRACT_ADDRESS={address}", text)
    else:
        text += f"\nCONTRACT_ADDRESS={address}\n"
    env_path.write_text(text, encoding="utf-8")
    print(f"\nCONTRACT_ADDRESS written to .env")
    print("Put this address in the README - judges need it to check the record.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Day 1, step 0: prove the environment works before writing any pipeline.

Checks imports, downloads the model weights, and reports which keys are present.
Run this first. If it fails, nothing else can work.

    python scripts/day1_check.py
"""

import _bootstrap  # noqa: F401

import sys


def main() -> int:
    print("=== environment ===")
    print(f"python  {sys.version.split()[0]}")

    try:
        import torch

        print(f"torch   {torch.__version__}  cuda={torch.cuda.is_available()}")
    except Exception as e:
        print(f"FAIL torch: {e}")
        return 1

    try:
        import facenet_pytorch

        print(f"facenet-pytorch {getattr(facenet_pytorch, '__version__', 'ok')}")
    except Exception as e:
        print(f"FAIL facenet-pytorch: {e}")
        return 1

    from facepipe import config

    print("\n=== .env keys ===")
    for name in ("SERPAPI_KEY", "IMGBB_KEY"):
        val = getattr(config, name)
        print(f"{name:14} {'set (' + val[:6] + '...)' if val else 'MISSING'}")
    print(f"{'MATCH_THRESHOLD':14} {config.MATCH_THRESHOLD}")

    print("\n=== downloading model weights (first run only) ===")
    from facepipe.faces import warm_up

    device = warm_up()
    print(f"models loaded on: {device}")

    print("\nOK - environment is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

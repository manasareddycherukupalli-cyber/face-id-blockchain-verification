"""Day 1, step 2: one full search-and-verify run on a single image.

Costs one SerpAPI credit (cached afterwards). Dumps the raw Lens JSON so you can
see the real response shape before building anything on top of it.

    python scripts/day1_probe.py data/scout/subject_a.jpg
    python scripts/day1_probe.py data/scout/subject_a.jpg --fresh
"""

import _bootstrap  # noqa: F401

import argparse
import json

from facepipe import config
from facepipe.probe import probe_image


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--fresh", action="store_true", help="bypass the Lens cache")
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--threshold", type=float, default=None)
    args = ap.parse_args()

    config.require("SERPAPI_KEY", "IMGBB_KEY")

    result = probe_image(
        args.image,
        fresh=args.fresh,
        verify=not args.no_verify,
        threshold=args.threshold,
    )

    config.OUT.mkdir(parents=True, exist_ok=True)
    dest = config.OUT / f"probe_{result['image']}.json"
    dest.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nreport -> {dest}")

    if result.get("verified"):
        best = result["verified"][0]
        print(f"best match: {best['score']:+.3f}  {best['link']}")
    else:
        print("no verified social match - do not use this subject in the recording")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

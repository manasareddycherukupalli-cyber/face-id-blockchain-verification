"""Day 1, step 3: the day's real work - find subjects that reliably produce
verified social-media matches, BEFORE the camera is rolling.

Drop one photo per candidate in data/scout/ (name the file after the person),
then run this. It reports, per subject, how many Lens results were social, how
many thumbnails had a detectable face, and the best verified cosine score.

Pick the two highest scorers for the recording. If nothing clears the bar, the
plan needs rework today - not on day 3.

    python scripts/day1_scout.py            # ~1 SerpAPI credit per subject
    python scripts/day1_scout.py --fresh
"""

import _bootstrap  # noqa: F401

import argparse
import json
import traceback

from facepipe import config
from facepipe.probe import probe_image

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--max-verify", type=int, default=15)
    args = ap.parse_args()

    config.require("SERPAPI_KEY", "IMGBB_KEY")

    folder = config.DATA / "scout"
    images = sorted(p for p in folder.glob("*") if p.suffix.lower() in IMG_EXT) \
        if folder.exists() else []
    if not images:
        print(f"Put one photo per candidate subject in {folder} and re-run.")
        return 1

    print(f"scouting {len(images)} subjects "
          f"(~{len(images)} SerpAPI credits)\n")

    results = []
    for path in images:
        print("=" * 72)
        print(path.stem)
        print("=" * 72)
        try:
            results.append(probe_image(
                path, fresh=args.fresh, max_verify=args.max_verify))
        except Exception:
            traceback.print_exc()
            results.append({"image": path.name, "error": "exception"})
        print()

    print("=" * 72)
    print(f"{'subject':<24}{'total':>7}{'social':>8}{'verified':>10}{'best':>8}")
    print("=" * 72)
    for r in results:
        verified = r.get("verified") or []
        best = f"{verified[0]['score']:+.3f}" if verified else "-"
        print(f"{r['image'][:23]:<24}{r.get('total_matches', 0):>7}"
              f"{r.get('social_candidates', 0):>8}{len(verified):>10}{best:>8}")

    usable = [r for r in results if r.get("verified")]
    print("\n" + ("-" * 72))
    if len(usable) >= 2:
        print("GO: at least two viable subjects. Use these in the recording:")
        for r in sorted(usable, key=lambda r: -r["verified"][0]["score"])[:2]:
            print(f"  {r['image']}  best {r['verified'][0]['score']:+.3f}  "
                  f"{r['verified'][0]['link']}")
    elif len(usable) == 1:
        print("PARTIAL: only one viable subject. Scout more candidates today -")
        print("the two-subject demo is your main anti-hardcoding evidence.")
    else:
        print("STOP: no subject produced a verified social match.")
        print("Before changing the design, check in this order:")
        print("  1. Are the Lens results social at all? (see per-subject domains)")
        print("  2. Are thumbnails yielding detectable faces? (undetectable count)")
        print("  3. Is MATCH_THRESHOLD too strict? (run day1_calibrate.py)")
        print("Only then consider adding a second search engine.")

    config.OUT.mkdir(parents=True, exist_ok=True)
    dest = config.OUT / "scout_report.json"
    dest.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nfull report -> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

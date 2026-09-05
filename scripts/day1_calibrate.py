"""Day 1, step 1: derive MATCH_THRESHOLD from real numbers instead of guessing.

Layout expected:

    data/calibrate/
        person_a/  photo1.jpg  photo2.jpg  photo3.jpg
        person_b/  photo1.jpg  photo2.jpg
        person_c/  ...

Use 3+ different photos per person (different angle, lighting, year - not crops
of the same shot, which would flatter the numbers and mislead you).

Computes every pairwise cosine, splits them into same-person and
different-person populations, and reports the gap between them. A threshold is
only trustworthy if those two populations do not overlap.

    python scripts/day1_calibrate.py
"""

import _bootstrap  # noqa: F401

from itertools import combinations

import numpy as np

from facepipe import config
from facepipe.faces import cosine, embed_path

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def main() -> int:
    root = config.DATA / "calibrate"
    if not root.exists():
        print(f"Create {root} with one subfolder per person, 3+ photos each.")
        return 1

    people = sorted(p for p in root.iterdir() if p.is_dir())
    if len(people) < 2:
        print("Need at least 2 people to measure the different-person population.")
        return 1

    print("=== embedding ===")
    vectors = {}
    for person in people:
        photos = sorted(p for p in person.iterdir() if p.suffix.lower() in IMG_EXT)
        for photo in photos:
            vec = embed_path(photo)
            status = "ok" if vec is not None else "NO FACE DETECTED"
            print(f"  {person.name}/{photo.name:<28} {status}")
            if vec is not None:
                vectors[(person.name, photo.name)] = vec

    if len(vectors) < 4:
        print("\nToo few usable faces to calibrate.")
        return 1

    same, diff = [], []
    print("\n=== pairwise cosine ===")
    for (ka, va), (kb, vb) in combinations(vectors.items(), 2):
        score = cosine(va, vb)
        is_same = ka[0] == kb[0]
        (same if is_same else diff).append(score)
        tag = "SAME" if is_same else "diff"
        print(f"  {tag}  {score:+.3f}  {ka[0]}/{ka[1]}  vs  {kb[0]}/{kb[1]}")

    same, diff = np.array(same), np.array(diff)
    print("\n=== populations ===")
    print(f"  same-person  n={len(same):<3} min={same.min():+.3f} "
          f"mean={same.mean():+.3f} max={same.max():+.3f}")
    print(f"  diff-person  n={len(diff):<3} min={diff.min():+.3f} "
          f"mean={diff.mean():+.3f} max={diff.max():+.3f}")

    gap = same.min() - diff.max()
    print(f"\n  separation gap: {gap:+.3f}")

    if gap > 0:
        suggested = round((same.min() + diff.max()) / 2, 2)
        print(f"  Populations are cleanly separated.")
        print(f"  -> set MATCH_THRESHOLD={suggested} in .env")
        margin = min(same.min() - suggested, suggested - diff.max())
        print(f"     (margin either side: {margin:.3f})")
    else:
        print("  WARNING: populations OVERLAP. A single threshold will produce")
        print("  false positives or false negatives. Options: use better-quality")
        print("  photos, or pick a conservative threshold and document the")
        print("  error rate honestly in the README.")
        print(f"  -> conservative choice: MATCH_THRESHOLD={round(float(same.mean()), 2)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

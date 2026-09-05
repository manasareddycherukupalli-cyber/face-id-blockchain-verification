"""Day 1, step 0.5: prove the face half works, with no API keys and no credits.

Downloads a few public-domain portraits, embeds them, and checks that the
same-person score lands well above the different-person scores. If this passes,
detection, embedding and cosine comparison are all sound, and any later failure
is in the search half - which halves your debugging surface.

    python scripts/day1_smoke.py
"""

import _bootstrap  # noqa: F401

from facepipe.faces import cosine, embed, fetch_image

BASE = "https://commons.wikimedia.org/wiki/Special:FilePath/"
SAMPLES = [
    ("obama_a", "President_Barack_Obama.jpg"),
    ("obama_b", "Obama_Portrait_2006.jpg"),
    ("merkel", "Angela_Merkel._Tallinn_Digital_Summit.jpg"),
    ("pichai", "Sundar_Pichai_-_2023_(cropped).jpg"),
]


def main() -> int:
    vecs = {}
    for name, filename in SAMPLES:
        url = f"{BASE}{filename}?width=600"
        try:
            vec = embed(fetch_image(url))
        except Exception as e:
            print(f"  {name:<10} fetch failed: {type(e).__name__}")
            continue
        print(f"  {name:<10} {'embedded' if vec is not None else 'NO FACE DETECTED'}")
        if vec is not None:
            vecs[name] = vec

    if "obama_a" not in vecs or "obama_b" not in vecs:
        print("\nCould not embed both same-person samples; cannot judge separation.")
        return 1

    print("\n=== scores ===")
    same = cosine(vecs["obama_a"], vecs["obama_b"])
    print(f"  SAME  obama_a vs obama_b   {same:+.3f}")

    others = []
    for name in ("merkel", "pichai"):
        if name in vecs:
            score = cosine(vecs["obama_a"], vecs[name])
            others.append(score)
            print(f"  diff  obama_a vs {name:<9} {score:+.3f}")

    print()
    if others and same > max(others) + 0.15:
        print(f"PASS - same-person scores {same - max(others):+.3f} above the "
              f"nearest different-person score.")
        print("The face half of the pipeline is sound.")
        return 0
    print("FAIL - separation is too small. Investigate before building further.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

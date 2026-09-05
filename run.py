"""Face ID + Blockchain Verification - the full pipeline, one command.

    python run.py path/to/photo.jpg
    python run.py photo.jpg --no-chain     # search and verify only, no tx
    python run.py --verify out/records/<name>.json

Stages:
    1. detect and encode the face in the input photo
    2. host the image so a reverse-image engine can read it
    3. genuine Google Lens reverse-image search (SerpAPI)
    4. keep only results on social media domains
    5. re-encode each result's thumbnail and compare it to the query face
    6. accept matches above the similarity threshold
    7. anchor the best match on Base Sepolia
    8. re-hash the local record and confirm the chain agrees

Nothing is hardcoded: every candidate comes back from a live search and carries
a clickable source URL.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from facepipe import chain, config  # noqa: E402
from facepipe.probe import probe_image  # noqa: E402

RECORDS = config.OUT / "records"


def rule(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image", nargs="?", help="input photo containing one face")
    ap.add_argument("--verify", metavar="RECORD_JSON",
                    help="verify a previously anchored record and exit")
    ap.add_argument("--fresh", action="store_true",
                    help="bypass the local Lens cache (spends a search credit)")
    ap.add_argument("--no-chain", action="store_true",
                    help="run the search and verification, but write nothing on-chain")
    ap.add_argument("--threshold", type=float, default=None,
                    help=f"cosine threshold (default {config.MATCH_THRESHOLD})")
    args = ap.parse_args()

    if args.verify:
        rule("VERIFY A PREVIOUSLY ANCHORED RECORD")
        ok = chain.verify(args.verify)
        return 0 if ok else 1

    if not args.image:
        ap.error("give an image path, or --verify a record")

    started = datetime.now(timezone.utc)
    rule(f"FACE ID + BLOCKCHAIN VERIFICATION   {started.isoformat(timespec='seconds')}")
    print(f"input: {args.image}")
    print(f"threshold: {args.threshold or config.MATCH_THRESHOLD}")

    rule("STAGES 1-6: DETECT, SEARCH, VERIFY")
    result = probe_image(
        args.image, fresh=args.fresh, threshold=args.threshold)

    if result.get("error"):
        print(f"\nstopped: {result['error']}")
        return 1

    if not result["verified"]:
        # A clean no-match is a correct outcome, not a crash. Writing an
        # unverified claim to an immutable ledger would be the actual failure.
        rule("NO VERIFIED MATCH")
        print(f"{result['total_matches']} visual matches, "
              f"{result['social_candidates']} on social domains, "
              f"none above the threshold.")
        print("Nothing written on-chain - an unverified claim must not be made")
        print("permanent. This is the pipeline working correctly, not failing.")
        return 2

    best = result["verified"][0]
    rule("BEST VERIFIED MATCH")
    print(f"  platform:   {best['source']}")
    print(f"  similarity: {best['score']:+.4f}  (threshold {result['threshold']})")
    print(f"  post:       {best['link']}")
    if len(result["verified"]) > 1:
        print(f"  ({len(result['verified'])} matches passed; showing the strongest)")

    record = chain.build_record(result, best)
    RECORDS.mkdir(parents=True, exist_ok=True)
    record_path = RECORDS / f"{Path(args.image).stem}.json"
    # Written in the same canonical form that gets hashed, so the file on disk
    # is byte-for-byte what the on-chain hash commits to.
    record_path.write_bytes(chain.canonical_json(record))
    print(f"\n  canonical record -> {record_path}")

    if args.no_chain:
        print("\n--no-chain: stopping before the on-chain write.")
        return 0

    rule("STAGE 7: ANCHOR ON BASE SEPOLIA")
    tx = chain.anchor(record)

    rule("STAGE 8: VERIFY THE ANCHORED RECORD")
    ok = chain.verify(record_path)

    rule("RESULT")
    print(f"  match:    {best['link']}")
    print(f"  platform: {best['source']}  similarity {best['score']:+.4f}")
    print(f"  record:   {tx['record_hash']}")
    if not tx.get("duplicate"):
        print(f"  tx:       {tx['explorer']}")
    print(f"  verified: {'YES' if ok else 'NO'}")
    print(f"\n  elapsed: {(datetime.now(timezone.utc) - started).seconds}s")

    summary = {"run_at": started.isoformat(), "record": record,
               "chain": tx, "verified": ok, "search": {
                   "total_matches": result["total_matches"],
                   "social_candidates": result["social_candidates"],
                   "accepted": len(result["verified"]),
                   "rejected": len(result["rejected"]),
                   "undetectable_thumbnails": result["undetectable"]}}
    out = RECORDS / f"{Path(args.image).stem}.run.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"  full run log: {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

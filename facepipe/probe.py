"""Stages 1-6 of the pipeline: image in, verified social matches out.

This is the reusable core. Day 1 uses it for scouting; day 2 bolts the chain
write onto its output without changing it.

    encode query face
      -> host image publicly
      -> live Lens reverse-image search
      -> keep only social-media domains
      -> encode each Lens thumbnail and cosine-compare to the query face
      -> accept above threshold

The thumbnails come from Google's own CDN, not the social platform, so no
login wall is hit and no site's terms are strained.
"""

from pathlib import Path

from . import config, lens
from .faces import cosine, embed, embed_path, embedding_hash, fetch_image, sha256_file
from .imghost import upload


def probe_image(
    path,
    fresh: bool = False,
    verify: bool = True,
    max_verify: int = 25,
    threshold: float | None = None,
    log=print,
) -> dict:
    """Run the search-and-verify pipeline for one local image."""
    path = Path(path)
    threshold = config.MATCH_THRESHOLD if threshold is None else threshold

    log(f"[1/5] encoding query face: {path.name}")
    query_vec = embed_path(path)
    if query_vec is None:
        log("      NO FACE DETECTED - cannot proceed")
        return {"image": path.name, "error": "no_face_in_query"}
    log(f"      512-d embedding, sha256 {embedding_hash(query_vec)[:16]}...")

    log("[2/5] uploading to imgbb for a public URL")
    hosted = upload(path)
    log(f"      {hosted['url']}")

    log("[3/5] reverse-image search via Google Lens (SerpAPI)")
    payload = lens.search(hosted["url"], fresh=fresh)
    if payload.get("_from_cache"):
        log("      (served from local cache - pass --fresh to force a live call)")
    summary = lens.summarise(payload)
    log(f"      {summary['total']} visual matches, {summary['social']} on social domains")
    for domain, count in summary["top_domains"]:
        log(f"        {count:>3}  {domain}")

    result = {
        "image": path.name,
        "image_sha256": sha256_file(path),
        "hosted_url": hosted["url"],
        "query_embedding_sha256": embedding_hash(query_vec),
        "total_matches": summary["total"],
        "social_candidates": summary["social"],
        "threshold": threshold,
        "verified": [],
        "rejected": [],
        "undetectable": 0,
    }

    if not verify:
        return result

    candidates = summary["social_matches"][:max_verify]
    log(f"[4/5] verifying {len(candidates)} social candidates against the query face")
    if not candidates:
        log("      none to verify - this subject is not a viable demo subject")

    for i, match in enumerate(candidates, 1):
        link = match.get("link", "")
        thumb = match.get("thumbnail") or match.get("image")
        source = match.get("source") or lens.domain_of(link)
        if not thumb:
            result["undetectable"] += 1
            log(f"  {i:>2}. {source:<16} no thumbnail in response")
            continue
        try:
            face_vec = embed(fetch_image(thumb))
        except Exception as e:
            result["undetectable"] += 1
            log(f"  {i:>2}. {source:<16} thumbnail fetch failed: {type(e).__name__}")
            continue

        if face_vec is None:
            # Real and expected: Lens thumbnails are small, and MTCNN needs
            # roughly 20px of face. Documented as a known limitation.
            result["undetectable"] += 1
            log(f"  {i:>2}. {source:<16} no face detectable in thumbnail")
            continue

        score = cosine(query_vec, face_vec)
        row = {
            "score": round(score, 4),
            "source": source,
            "link": link,
            "title": match.get("title", ""),
            "thumbnail": thumb,
        }
        if score >= threshold:
            result["verified"].append(row)
            log(f"  {i:>2}. {source:<16} {score:+.3f}  ACCEPT  {link[:70]}")
        else:
            result["rejected"].append(row)
            log(f"  {i:>2}. {source:<16} {score:+.3f}  reject")

    result["verified"].sort(key=lambda r: -r["score"])
    log(f"[5/5] {len(result['verified'])} verified, "
        f"{len(result['rejected'])} below threshold, "
        f"{result['undetectable']} unusable thumbnails")
    return result

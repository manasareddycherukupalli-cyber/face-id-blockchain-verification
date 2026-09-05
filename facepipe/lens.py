"""Genuine reverse-image search via SerpAPI's Google Lens engine.

Nothing here is hardcoded: every candidate comes back from a live Lens query and
carries a real, clickable source URL.

Responses are cached to out/lens_cache/ keyed by the image URL, because the free
SerpAPI tier is ~100 searches/month and re-running a script should not silently
burn credits. Pass fresh=True to bypass the cache (the demo run always does).
"""

import hashlib
import json
import time
from urllib.parse import urlparse

import requests

from . import config

ENDPOINT = "https://serpapi.com/search"
CACHE_DIR = config.OUT / "lens_cache"


def _cache_path(image_url: str):
    key = hashlib.sha256(image_url.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{key}.json"


def search(image_url: str, fresh: bool = False, timeout: int = 90) -> dict:
    """Run a Lens reverse-image search. Returns the raw SerpAPI response."""
    config.require("SERPAPI_KEY")
    cache = _cache_path(image_url)

    if not fresh and cache.exists():
        payload = json.loads(cache.read_text(encoding="utf-8"))
        payload["_from_cache"] = True
        return payload

    started = time.time()
    r = requests.get(
        ENDPOINT,
        params={
            "engine": "google_lens",
            "url": image_url,
            "api_key": config.SERPAPI_KEY,
            "hl": "en",
            "country": "us",
        },
        timeout=timeout,
    )
    # SerpAPI puts a human-readable reason in the JSON body even on 4xx, so read
    # that before raising - a bare "429 Too Many Requests" hides the real cause
    # (e.g. an unactivated account, which is not a rate limit at all).
    try:
        payload = r.json()
    except ValueError:
        r.raise_for_status()
        raise RuntimeError(f"SerpAPI returned non-JSON (HTTP {r.status_code})")

    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"SerpAPI error (HTTP {r.status_code}): {payload['error']}")
    r.raise_for_status()

    payload["_elapsed_s"] = round(time.time() - started, 2)
    payload["_from_cache"] = False
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def visual_matches(payload: dict) -> list:
    """Pull the candidate list out of a Lens response.

    SerpAPI has shuffled these keys between API revisions, so accept any of them
    rather than assuming one shape.
    """
    for key in ("visual_matches", "image_results", "exact_matches"):
        if payload.get(key):
            return payload[key]
    return []


def domain_of(url: str) -> str:
    host = urlparse(url or "").netloc.lower()
    return host[4:] if host.startswith("www.") else host


def is_social(url: str) -> bool:
    host = domain_of(url)
    return any(host == d or host.endswith("." + d) for d in config.SOCIAL_DOMAINS)


def summarise(payload: dict) -> dict:
    """Counts by domain plus the social subset - the day-1 scouting signal."""
    matches = visual_matches(payload)
    social = [m for m in matches if is_social(m.get("link", ""))]
    domains = {}
    for m in matches:
        d = domain_of(m.get("link", "")) or "?"
        domains[d] = domains.get(d, 0) + 1
    return {
        "total": len(matches),
        "social": len(social),
        "social_matches": social,
        "top_domains": sorted(domains.items(), key=lambda kv: -kv[1])[:10],
    }

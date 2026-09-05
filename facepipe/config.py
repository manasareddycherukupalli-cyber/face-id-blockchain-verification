"""Shared configuration, loaded from .env at the project root."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()
IMGBB_KEY = os.getenv("IMGBB_KEY", "").strip()

# Derived from day1_calibrate.py, not guessed. See DAY1.md.
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.60"))

DATA = ROOT / "data"
OUT = ROOT / "out"

# A Lens result only satisfies "a real matching social media post" if it lives
# on one of these. Kept deliberately strict - broadening it to blogs and forums
# would inflate the hit rate at the cost of honestly meeting the requirement.
SOCIAL_DOMAINS = (
    "instagram.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "fb.com",
    "linkedin.com",
    "tiktok.com",
    "youtube.com",
    "threads.net",
    "threads.com",
    "reddit.com",
    "pinterest.com",
    "tumblr.com",
    "vk.com",
    "weibo.com",
    "mastodon.social",
    "bsky.app",
)


def require(*names: str) -> None:
    """Fail loudly and early if a needed key is missing from .env."""
    missing = [n for n in names if not globals().get(n)]
    if missing:
        raise SystemExit(
            f"Missing in .env: {', '.join(missing)}\n"
            f"Copy .env.example to .env and fill them in."
        )

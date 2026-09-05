"""Day 1, step 0.6: confirm both API keys actually work.

Costs ZERO SerpAPI search credits - it hits the account endpoint, not the search
endpoint, and reports how many searches you have left. The imgbb check does a
real upload of a tiny generated image, then hands you the delete URL.

    python scripts/day1_keys.py
"""

import _bootstrap  # noqa: F401

import io
import tempfile
from pathlib import Path

import requests
from PIL import Image

from facepipe import config


def check_serpapi() -> bool:
    if not config.SERPAPI_KEY:
        print("SERPAPI_KEY  MISSING from .env")
        return False
    try:
        r = requests.get(
            "https://serpapi.com/account",
            params={"api_key": config.SERPAPI_KEY},
            timeout=30,
        )
    except Exception as e:
        print(f"SERPAPI_KEY  network error: {type(e).__name__}: {e}")
        return False

    if r.status_code == 401:
        print("SERPAPI_KEY  REJECTED (401) - wrong key, check manage-api-key page")
        return False
    if not r.ok:
        print(f"SERPAPI_KEY  HTTP {r.status_code}: {r.text[:200]}")
        return False

    acct = r.json()
    left = acct.get("total_searches_left", acct.get("plan_searches_left", "?"))
    print(f"SERPAPI_KEY  OK")
    print(f"             plan:            {acct.get('plan_name', '?')}")
    print(f"             searches left:   {left}")
    print(f"             used this month: {acct.get('this_month_usage', '?')}")
    if isinstance(left, int) and left < 20:
        print("             WARNING: low. Budget ~1 credit per scouted subject,")
        print("             plus 2 for the recording. Use the cache for the rest.")
    return True


def check_imgbb() -> bool:
    if not config.IMGBB_KEY:
        print("IMGBB_KEY    MISSING from .env")
        return False

    # A tiny real PNG - imgbb rejects empty or non-image payloads.
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (20, 120, 70)).save(buf, format="PNG")
    tmp = Path(tempfile.gettempdir()) / "facepipe_keycheck.png"
    tmp.write_bytes(buf.getvalue())

    try:
        from facepipe.imghost import upload

        res = upload(tmp)
    except Exception as e:
        print(f"IMGBB_KEY    FAILED: {type(e).__name__}: {e}")
        return False
    finally:
        tmp.unlink(missing_ok=True)

    print("IMGBB_KEY    OK")
    print(f"             public url: {res['url']}")
    print(f"             delete url: {res['delete_url']}")

    # The URL must be publicly fetchable or SerpAPI cannot read it.
    try:
        head = requests.get(res["url"], timeout=20, stream=True)
        ok = head.ok and head.headers.get("content-type", "").startswith("image/")
        print(f"             publicly reachable: {'yes' if ok else 'NO'} "
              f"(HTTP {head.status_code}, {head.headers.get('content-type')})")
        return ok
    except Exception as e:
        print(f"             could not verify reachability: {type(e).__name__}")
        return False


def main() -> int:
    print("=== API keys ===")
    a = check_serpapi()
    print()
    b = check_imgbb()
    print()
    if a and b:
        print("Both keys work. Next: scouting (scripts/day1_scout.py).")
        return 0
    print("Fix the above before scouting - a bad key wastes an hour of confusion.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

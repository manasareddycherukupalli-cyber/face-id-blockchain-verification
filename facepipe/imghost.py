"""Make a local image publicly reachable.

SerpAPI's Lens endpoint takes a URL, not a file upload, so every run needs a
hosting hop. imgbb is used because it is a single keyed POST with no account
friction and returns a permanent direct-image URL.

The sha256 of the local bytes travels with the record, so the on-chain claim
stays checkable even if imgbb ever drops the file.
"""

import base64
from pathlib import Path

import requests

from . import config
from .faces import sha256_file

ENDPOINT = "https://api.imgbb.com/1/upload"


def upload(path, timeout: int = 60) -> dict:
    """Upload a local image. Returns {url, delete_url, sha256, bytes}."""
    config.require("IMGBB_KEY")
    path = Path(path)
    payload = base64.b64encode(path.read_bytes())

    r = requests.post(
        ENDPOINT,
        data={"key": config.IMGBB_KEY, "image": payload},
        timeout=timeout,
    )
    r.raise_for_status()
    body = r.json()
    if not body.get("success"):
        raise RuntimeError(f"imgbb upload failed: {body}")

    data = body["data"]
    return {
        "url": data["url"],                      # direct i.ibb.co image link
        "display_url": data.get("display_url"),
        "delete_url": data.get("delete_url"),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }

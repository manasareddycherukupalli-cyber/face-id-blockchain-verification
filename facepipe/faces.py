"""Face detection and embedding.

MTCNN locates the face, InceptionResnetV1 (VGGFace2 weights) turns the aligned
crop into a 512-d vector. Vectors are L2-normalised on the way out, so cosine
similarity is just a dot product.
"""

import hashlib
import io
from functools import lru_cache
from pathlib import Path

import numpy as np
import requests
import torch
from PIL import Image, ImageOps

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) facepipe/0.1"


@lru_cache(maxsize=1)
def _models():
    """Load models once. First call downloads ~110MB of weights."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    from facenet_pytorch import MTCNN, InceptionResnetV1

    mtcnn = MTCNN(
        image_size=160,
        margin=20,
        min_face_size=20,      # lowered from the default 20 matters for thumbnails
        post_process=True,
        select_largest=True,   # if several faces, take the most prominent
        device=device,
    )
    resnet = InceptionResnetV1(pretrained="vggface2").eval().to(device)
    return device, mtcnn, resnet


def warm_up() -> str:
    """Force the weight download now rather than mid-demo. Returns device name."""
    device, _, _ = _models()
    return str(device)


def load_image(src) -> Image.Image:
    """Open a local path or bytes as RGB, honouring EXIF rotation."""
    if isinstance(src, (bytes, bytearray)):
        img = Image.open(io.BytesIO(src))
    else:
        img = Image.open(Path(src))
    return ImageOps.exif_transpose(img).convert("RGB")


def fetch_image(url: str, timeout: int = 20) -> Image.Image:
    """Download an image URL (used for Lens-provided thumbnails)."""
    r = requests.get(url, timeout=timeout, headers={"User-Agent": _UA})
    r.raise_for_status()
    return load_image(r.content)


def embed(img: Image.Image):
    """Return an L2-normalised 512-d embedding, or None if no face was found."""
    _, mtcnn, resnet = _models()
    face = mtcnn(img)
    if face is None:
        return None
    with torch.no_grad():
        vec = resnet(face.unsqueeze(0)).squeeze(0).cpu().numpy()
    norm = np.linalg.norm(vec)
    if norm == 0:
        return None
    return vec / norm


def embed_path(path) -> "np.ndarray | None":
    return embed(load_image(path))


def cosine(a, b) -> float:
    """Cosine similarity of two normalised embeddings. Range roughly -1..1."""
    return float(np.dot(a, b))


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def embedding_hash(vec) -> str:
    """Stable hash of an embedding, for putting on-chain without the vector."""
    return hashlib.sha256(np.asarray(vec, dtype=np.float32).tobytes()).hexdigest()

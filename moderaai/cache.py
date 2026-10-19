"""The verdict cache in Firestore: the same input (under the same policy) is only sent to Gemini once an hour."""

import hashlib
import time

from google.cloud import firestore

from config import CACHE_TTL_SECONDS, MODERATION_POLICY, PROJECT_ID

db = firestore.Client(project=PROJECT_ID)
COLLECTION = "moderation_cache"


def text_key(text: str) -> str:
    # The policy is part of the key: otherwise a verdict cached under one policy (v2 strict) would be served
    # after a rollback to another (v1 standard), and the rollback would look like it changed nothing.
    return hashlib.sha256(f"{MODERATION_POLICY}:{text.strip().lower()}".encode("utf-8")).hexdigest()


def image_key(image: bytes) -> str:
    # The same image uploaded again (byte for byte) gets the cached verdict. Only the verdict is stored, never the image.
    return hashlib.sha256(f"{MODERATION_POLICY}:image:".encode("utf-8") + image).hexdigest()


def get_verdict(key: str) -> dict | None:
    doc = db.collection(COLLECTION).document(key).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    if time.time() - data["cached_at"] >= CACHE_TTL_SECONDS:
        return None  # expired: treated as a miss (the old entry is simply overwritten later)
    return {k: v for k, v in data.items() if k != "cached_at"}


def save_verdict(key: str, verdict: dict) -> None:
    db.collection(COLLECTION).document(key).set({**verdict, "cached_at": time.time()})

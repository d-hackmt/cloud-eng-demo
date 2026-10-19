"""Settings, read once from environment variables (Cloud Run gets them from --set-env-vars)."""

import os

PROJECT_ID = os.environ["PROJECT_ID"]
LOCATION = os.environ.get("LOCATION", "us-central1")
MODERATION_POLICY = os.environ.get("MODERATION_POLICY", "standard")  # "standard" or "strict"
# Gemini model IDs retire on a schedule: check this one is still current before deploying.
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-2.5-flash")
GEMINI_TIMEOUT_MS = int(os.environ.get("GEMINI_TIMEOUT_MS", "10000"))
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))
# Caps how much text one request can send to Gemini (and so what one request can cost).
MAX_TEXT_CHARS = int(os.environ.get("MAX_TEXT_CHARS", "5000"))
# Same idea for images: bigger uploads are refused before they reach Gemini.
MAX_IMAGE_BYTES = int(os.environ.get("MAX_IMAGE_BYTES", str(5 * 1024 * 1024)))

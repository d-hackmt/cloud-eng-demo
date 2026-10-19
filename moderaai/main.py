"""ModeraAI — a tiny content moderation API used as the demo service for Module 17.

Checks text (/moderate) and images (/moderate-image) with Gemini, and serves a simple web page at /.
This file only holds the web routes; the pieces live in their own modules:

  config.py   settings from environment variables
  schemas.py  the shape of a verdict
  prompts.py  the instructions Gemini gets (standard or strict policy)
  gemini.py   calling Gemini: time limit, retries, safety blocks
  cache.py    the verdict cache in Firestore
  images.py   checking an upload is a JPEG, PNG or WebP
"""

import logging
import os

from flask import Flask, jsonify, request

import cache
import gemini
import prompts
from config import MAX_IMAGE_BYTES, MAX_TEXT_CHARS, MODERATION_POLICY
from images import image_type
from schemas import ImageModerationResult, ModerationResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("moderaai")

app = Flask(__name__)
# Flask refuses any request body bigger than this (the image plus a little room for the form around it).
app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_BYTES + 64 * 1024


def moderate_with_cache(key: str, contents, instructions: str, schema: type[ModerationResult]):
    cached = cache.get_verdict(key)
    if cached is not None:
        return jsonify({**cached, "cache_hit": True, "policy": MODERATION_POLICY}), 200

    try:
        result = gemini.call_gemini(contents, instructions, schema)
    except Exception:
        # The full error goes to Cloud Run's logs; the caller gets a plain message, not our internals.
        logger.exception("moderation failed")
        return jsonify({"error": "moderation failed"}), 502

    verdict = result.model_dump()
    cache.save_verdict(key, verdict)
    return jsonify({**verdict, "cache_hit": False, "policy": MODERATION_POLICY}), 200


# A simple web page for trying the API in a browser (static/index.html).
@app.route("/", methods=["GET"])
def ui():
    return app.send_static_file("index.html")


# Not "/healthz": Cloud Run reserves that path on its public URLs and answers 404 itself.
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "moderaai", "policy": MODERATION_POLICY}), 200


@app.route("/moderate", methods=["POST"])
def moderate():
    body = request.get_json(force=True, silent=True)
    text = body.get("text") if isinstance(body, dict) else None
    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "field 'text' is required and must be a non-empty string"}), 400
    if len(text) > MAX_TEXT_CHARS:
        return jsonify({"error": f"field 'text' is longer than {MAX_TEXT_CHARS} characters"}), 413

    return moderate_with_cache(cache.text_key(text), text, prompts.text_instructions(), ModerationResult)


@app.route("/moderate-image", methods=["POST"])
def moderate_image():
    upload = request.files.get("image")
    if upload is None:
        return jsonify({"error": "upload the image as a form field named 'image'"}), 400
    data = upload.read()
    if not data:
        return jsonify({"error": "the uploaded image is empty"}), 400
    if len(data) > MAX_IMAGE_BYTES:
        return jsonify({"error": f"the image is larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB"}), 413
    mime_type = image_type(data)
    if mime_type is None:
        return jsonify({"error": "only JPEG, PNG and WebP images are accepted"}), 415

    contents = [gemini.image_part(data, mime_type), "Review this image."]
    return moderate_with_cache(cache.image_key(data), contents, prompts.image_instructions(), ImageModerationResult)


@app.errorhandler(413)
def too_large(_error):
    # Flask's own 413 (body over MAX_CONTENT_LENGTH) is an HTML page; answer in JSON like everything else.
    return jsonify({"error": f"the upload is larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB"}), 413


@app.route("/stats", methods=["GET"])
def stats():
    return jsonify({"gemini_call_count": gemini.call_count}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

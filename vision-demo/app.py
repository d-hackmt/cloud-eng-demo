"""Vision SafeSearch demo — a small local app, separate from ModeraAI.

Upload an image; Cloud Vision's SafeSearch scores it (adult, violence, racy, medical, spoof) and this app turns the
scores into a decision with one simple rule. SafeSearch only scores; the rule below is what makes the decision.

Run:  uv run python vision-demo/app.py   then open http://localhost:8081
"""

import os

from flask import Flask, jsonify, request, send_from_directory
from google.cloud import vision

PROJECT_ID = os.environ.get("PROJECT_ID", "gcp-fde-project")
MAX_IMAGE_BYTES = 5 * 1024 * 1024
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "moderaai", "static", "samples")

# The decision rule: block when any of these categories is at least this likely.
BLOCK_CATEGORIES = ("adult", "violence", "racy")
BLOCK_AT = "LIKELY"
LEVELS = ["UNKNOWN", "VERY_UNLIKELY", "UNLIKELY", "POSSIBLE", "LIKELY", "VERY_LIKELY"]

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_BYTES + 64 * 1024
# quota_project_id: with your own gcloud login, Google needs to know which project the Vision calls are billed to.
client = vision.ImageAnnotatorClient(client_options={"quota_project_id": PROJECT_ID})


def is_image(data: bytes) -> bool:
    return data.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")) or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")


@app.route("/")
def index():
    return send_from_directory(os.path.dirname(__file__), "index.html")


@app.route("/samples/<path:name>")
def samples(name):
    # The same example images ModeraAI uses, so the two can be compared side by side.
    return send_from_directory(SAMPLES_DIR, name)


@app.route("/check", methods=["POST"])
def check():
    upload = request.files.get("image")
    data = upload.read() if upload else b""
    if not data:
        return jsonify({"error": "upload an image as a form field named 'image'"}), 400
    if not is_image(data):
        return jsonify({"error": "only JPEG, PNG and WebP images are accepted"}), 415

    response = client.safe_search_detection(image=vision.Image(content=data))
    if response.error.message:
        return jsonify({"error": f"Vision API error: {response.error.message}"}), 502

    annotation = response.safe_search_annotation
    scores = {
        category: vision.Likelihood(getattr(annotation, category)).name
        for category in ("adult", "violence", "racy", "medical", "spoof")
    }
    reasons = [c for c in BLOCK_CATEGORIES if LEVELS.index(scores[c]) >= LEVELS.index(BLOCK_AT)]
    return jsonify({
        "decision": "block" if reasons else "allow",
        "reasons": reasons,
        "rule": f"block if {', '.join(BLOCK_CATEGORIES)} is {BLOCK_AT} or higher",
        "scores": scores,
    })


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "the image is larger than 5 MB"}), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8081)

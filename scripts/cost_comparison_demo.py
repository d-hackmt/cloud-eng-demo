"""Topic 10 - Cost Optimization.

1) Sends the same moderation prompt through Gemini Flash and Gemini Pro,
   printing real token counts and an estimated cost for each.
2) Replays a small batch of requests (half duplicates) against a running
   ModeraAI instance and reads /stats before and after, to prove caching
   reduced the number of REAL Gemini calls below the number of incoming
   requests.

Prices below are illustrative per-1K-token estimates for teaching purposes -
always check the current Vertex AI pricing page before quoting a real number
to students. The model IDs below are also worth re-checking at build time -
Gemini model IDs retire on a schedule (gemini-2.0-flash-001 was discontinued
June 1, 2026; there was never a stable "gemini-2.0-pro-001" GA release at
all - Gemini 2.0 Pro only ever shipped as an experimental preview). Check
https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini
for the current GA lineup before recording this module.
"""

import os

import requests
from google import genai

PROJECT_ID = os.environ["PROJECT_ID"]
LOCATION = os.environ.get("LOCATION", "us-central1")
SERVICE_URL = os.environ.get("SERVICE_URL", "http://localhost:8080")

# Illustrative estimated $ per 1K tokens (input+output blended) - for teaching only.
ESTIMATED_COST_PER_1K_TOKENS = {
    "gemini-2.5-flash": 0.0001,
    "gemini-2.5-pro": 0.0025,
}

SAMPLE_TEXT = "This new policy is completely unfair and I'm furious about it."


def compare_models():
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    prompt = f'You are a content moderation system. Review this text: "{SAMPLE_TEXT}"'

    print("== Model cost comparison (same prompt, two models) ==\n")
    for model_name, cost_per_1k in ESTIMATED_COST_PER_1K_TOKENS.items():
        response = client.models.generate_content(model=model_name, contents=prompt)
        usage = response.usage_metadata
        total_tokens = usage.total_token_count
        estimated_cost = (total_tokens / 1000) * cost_per_1k
        print(f"{model_name}:")
        print(f"  input tokens:  {usage.prompt_token_count}")
        print(f"  output tokens: {usage.candidates_token_count}")
        print(f"  total tokens:  {total_tokens}")
        print(f"  estimated cost: ${estimated_cost:.6f}\n")


def prove_caching_saves_real_calls():
    print("== Caching's real savings (request counter, not an estimate) ==\n")
    before = requests.get(f"{SERVICE_URL}/stats", timeout=10).json()["gemini_call_count"]

    texts = [
        "This is a test comment.",
        "This is a test comment.",  # duplicate -> cache hit
        "Another unique comment here.",
        "This is a test comment.",  # duplicate -> cache hit
        "Another unique comment here.",  # duplicate -> cache hit
        "A third, brand new comment.",
    ]
    for text in texts:
        requests.post(f"{SERVICE_URL}/moderate", json={"text": text}, timeout=30)

    after = requests.get(f"{SERVICE_URL}/stats", timeout=10).json()["gemini_call_count"]
    real_calls = after - before

    print(f"Incoming requests: {len(texts)}")
    print(f"Real Gemini calls: {real_calls}")
    print(f"Calls avoided by caching: {len(texts) - real_calls}")


if __name__ == "__main__":
    compare_models()
    prove_caching_saves_real_calls()

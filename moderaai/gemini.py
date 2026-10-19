"""Calling Gemini: one client with a time limit, retries with backoff, and safety blocks treated as verdicts."""

import logging

from google import genai
from google.genai import types
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

from config import GEMINI_TIMEOUT_MS, LOCATION, MODEL_NAME, PROJECT_ID
from schemas import ModerationResult

logger = logging.getLogger("moderaai")

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
    http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
)

# In-memory counter of real Gemini calls (shown by /stats). Resets on cold start; good enough for a demo.
call_count = 0

# Gemini's own safety filter sometimes refuses to process an input at all. That's a verdict, not an error.
BLOCK_REASONS = {"SAFETY", "PROHIBITED_CONTENT", "IMAGE_SAFETY", "BLOCKLIST", "SPII"}


def blocked_reason(response) -> str | None:
    feedback = getattr(response, "prompt_feedback", None)
    if feedback is not None and feedback.block_reason:
        return getattr(feedback.block_reason, "name", str(feedback.block_reason))
    for candidate in response.candidates or []:
        reason = getattr(candidate.finish_reason, "name", str(candidate.finish_reason))
        if reason in BLOCK_REASONS:
            return reason
    return None


# before_sleep_log writes one line per retry, so the attempts show up in Cloud Run's logs.
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8),
       before_sleep=before_sleep_log(logger, logging.WARNING))
def call_gemini(contents, instructions: str, schema: type[ModerationResult]) -> ModerationResult:
    global call_count
    call_count += 1
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=contents,
        config={
            "system_instruction": instructions,
            "response_mime_type": "application/json",
            "response_schema": schema,
        },
    )
    if not response.text:
        reason = blocked_reason(response)
        if reason:
            return schema.model_validate({
                "flagged": True,
                "category": "blocked_by_gemini_safety_filter",
                "reasoning": f"Gemini refused to process this content ({reason}).",
                "text_in_image": "",
            })
        raise ValueError("Gemini returned an empty response")  # retried, like any other failure
    return schema.model_validate_json(response.text)


def image_part(data: bytes, mime_type: str):
    return types.Part.from_bytes(data=data, mime_type=mime_type)

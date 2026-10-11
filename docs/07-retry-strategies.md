# 7. Retry Strategies

## What Is It?

If you call someone and the line drops, you don't give up forever — you call again. A retry strategy is ModeraAI doing that automatically: if a call to Gemini fails for a reason that's likely temporary (a network blip, a momentary overload), it tries again a couple of times before giving up, instead of failing the user's request on the very first hiccup.

## Why It Matters for AI Engineers

Calls to any external API — Gemini included — fail sometimes for reasons that have nothing to do with your code and go away on their own a second later. Without retries, a perfectly healthy service reports errors on a normal day just because of ordinary network noise. With retries, most of those failures become invisible to the caller — the system just quietly tries again and succeeds.

## Key Concepts

| Term | Definition |
|---|---|
| Transient failure | A temporary error likely to succeed if retried (vs. a permanent one that never will) |
| Exponential backoff | Waiting longer between each retry attempt (1s, then 2s, then 4s...) instead of hammering immediately |
| `tenacity` | The Python library used here to add retry behavior with a decorator |
| Max attempts | A hard cap so retries don't loop forever on a truly broken dependency |

## How It Fits Together

```mermaid
flowchart TD
    A[Call Gemini] --> B{Success?}
    B -->|Yes| C[Return result]
    B -->|No, attempt 1| D[Wait 1s, retry]
    D --> E{Success?}
    E -->|No, attempt 2| F[Wait 2s, retry]
    F --> G{Success?}
    G -->|No, attempt 3 - out of retries| H[Return real error]
    G -->|Yes| C
```

## Hands-On

```python
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

# 3 attempts, waiting 1 s then 2 s; before_sleep_log writes one log line per retry
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8),
       before_sleep=before_sleep_log(logger, logging.WARNING))
def call_gemini(text, simulate_transient_failure):
    return client.models.generate_content(...)
```

```bash
# The built-in switch that fails the first two attempts on purpose
curl -w "\nTime: %{time_total}s\n" -X POST "https://moderaai-1039893753206.us-central1.run.app/moderate?simulate_transient_failure=true" \
  -H "Content-Type: application/json" -d '{"text": "retry demo text"}'
```

The switch only works when the service is deployed with `ENABLE_DEMO_SWITCHES=true` (the demo deploys set it). Left
off, the parameter is ignored, so nobody can use it on a real service.

## How We Test It

`?simulate_transient_failure=true` makes the call fail the first two attempts on purpose and succeed on the third — deliberately engineered, not left to chance. The caller still gets a clean `200 OK` with a real verdict; it just takes longer (**6.4 s** against 2.4 s normally on our run: the 1 s and 2 s waits plus the extra attempts). The logs show each retry:

```bash
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=moderaai AND textPayload:"Retrying"' \
  --project=gcp-fde-project --limit=10 --order=asc --format="value(timestamp,textPayload)"
# -> WARNING:moderaai:Retrying main.call_gemini in 1 seconds as it raised ConnectionError: Simulated transient failure (attempt 1).
# -> WARNING:moderaai:Retrying main.call_gemini in 2 seconds as it raised ConnectionError: Simulated transient failure (attempt 2).
```

## Common Pitfalls

- Retrying *every* kind of failure, including permanent ones (like a malformed request) — that just wastes time before failing anyway
- No backoff (retrying instantly, back-to-back) — hammers an already-struggling dependency instead of giving it room to recover
- No max attempts — an infinite retry loop turns a transient failure into a hung request (this is exactly what topic 8, Timeouts, guards against)

## Quick Recap

1. What's the difference between a transient and a permanent failure, and why does that distinction matter for retries?
2. Why does the wait time increase between each retry attempt instead of staying constant?
3. In the demo, why does the caller's final response look identical to a request that never failed at all?

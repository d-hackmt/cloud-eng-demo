# 8. Timeouts

## What Is It?

If you ask someone a question and they just stand there silently, at some point you stop waiting and walk away rather than standing there forever. A timeout is ModeraAI doing that: if a call to Gemini takes too long, it gives up and returns a clear error, instead of leaving the caller hanging indefinitely.

## Why It Matters for AI Engineers

A hung request is worse than a failed one — it ties up an instance, a connection, and the caller's patience, all for an answer that may never come. Retries (topic 7) handle failures that happen *fast*; timeouts handle the failure that happens *slow* — the call that never technically errors, it just never finishes. Both are needed; neither replaces the other.

## Key Concepts

| Term | Definition |
|---|---|
| Client-side timeout | A limit set in the code calling Gemini (the `google-genai` SDK's `HttpOptions`) |
| Cloud Run request timeout | A platform-level ceiling on how long Cloud Run itself will wait for a response (configurable, default 300s) |
| Fail fast | The principle that a fast, clear failure is better than a slow, silent hang |

## How It Fits Together

```text
call Gemini
      ├── answers within 10 s ──► return the result
      └── no answer in 10 s ────► abort the call ──► retry (topic 7) ──► still nothing: clean error, HTTP 502

behind everything: Cloud Run cuts off any request still running after 30 s ──► HTTP 504
```

## Hands-On

```python
from google.genai.types import HttpOptions

client = genai.Client(vertexai=True, http_options=HttpOptions(timeout=10000))  # 10s, in ms
```

```bash
# Cloud Run's own backstop timeout is set at deploy time: --timeout=30 (see topic 1's deploy)
```

## How We Test It

There are two safety nets:

1. **The app's Gemini timeout (tested).** A temporary revision is deployed with the timeout set to 1 ms, at 0% traffic with its own address. Calling it gives a clean HTTP **502** `{"error": "moderation failed"}` after the retries, instead of a request that hangs. The real error (a connection timeout) goes to the logs, not to the caller. Then the setting is put back to 10 seconds. Full commands in [`commands.md`](../commands.md), topics 7 and 8.
2. **Cloud Run's timeout (a setting).** `--timeout=30` makes Cloud Run cut off any request that runs past 30 seconds with an HTTP **504**, whatever the code does. On the original run, a request made to stall on purpose was cut off at 30.4 s.

Cloud Run's `--timeout` is the backstop that always holds, because the platform enforces it.

## Common Pitfalls

- Relying only on the timeout in your code and never setting Cloud Run's own `--timeout` — the platform's limit catches the hangs your code doesn't- Setting a timeout so short that normal, healthy Gemini calls get cut off — tune it against real observed latency, not a guess
- Confusing a timeout with a retry — a timed-out call isn't automatically retried unless you explicitly combine both (which this module's `main.py` does)

## Quick Recap

1. What's the difference between the kind of failure retries catch and the kind timeouts catch?
2. Why is Cloud Run's `--timeout` flag described as the "dependable backstop" in this topic?
3. What would happen to a caller if ModeraAI had retries but no timeout at all, and a call genuinely hung?

# 6. Caching

## What Is It?

If two different people ask you the exact same question five minutes apart, you don't re-derive the answer from scratch the second time — you just remember what you said. Caching is ModeraAI doing the same thing: if it's already moderated this exact text before, it hands back the saved verdict instead of calling Gemini again.

## Why It Matters for AI Engineers

Every Gemini call costs real money and real time. In a moderation use case, the same text shows up more than once — a popular comment gets copy-pasted, a spam bot sends the same message repeatedly, a user edits and resubmits the same draft. Caching is one of the highest-leverage cost and latency wins available in an AI service, for close to zero added complexity.

## Key Concepts

| Term | Definition |
|---|---|
| `content_hash()` | A SHA-256 hash of the moderation policy plus the trimmed, lower-cased text — used as the cache key |
| Cache hit | The requested text was already moderated; return the saved result |
| Cache miss | New text; call Gemini, then save the result for next time |
| TTL (Time To Live) | How long a cached result stays valid before it's treated as stale (this module: 3600s / 1 hour) |

## How It Fits Together

```mermaid
flowchart TD
    A[POST /moderate] --> B[hash the text]
    B --> C{Found in Firestore<br/>cache and not expired?}
    C -->|Yes| D["Return cached result<br/>cache_hit: true"]
    C -->|No| E[Call Gemini]
    E --> F[Save result + timestamp to Firestore]
    F --> G["Return fresh result<br/>cache_hit: false"]
```

## Hands-On

```bash
# Run it twice: the first is a cache miss (real Gemini call), the second a cache hit
curl -w "\nTime: %{time_total}s\n" -X POST https://moderaai-1039893753206.us-central1.run.app/moderate \
  -H "Content-Type: application/json" -d '{"text": "Nice write-up, I learned a lot from it"}'
```

## How We Test It

Call `/moderate` with the identical text twice in a row and look at two things in the JSON response: the `cache_hit` field (`false` then `true`) and the response time. On our run the first call took **2.9 s** (a real Gemini round trip) and the repeats **0.46 s** (a Firestore read only). That timing gap *is* the proof; no logs needed to see it.

Why the policy is in the key: v1 (standard) and v2 (strict) can give different verdicts for the same text. With a text-only key, one version would be handed the other's cached answer (see topic 5).

## Common Pitfalls

- Hashing the raw text without normalizing (e.g. trimming whitespace/casing) — near-identical inputs miss the cache when they arguably shouldn't
- Caching forever with no TTL — stale results linger even after you improve the moderation prompt
- Forgetting the cache is keyed on exact text — this is a moderation *result* cache, not a semantic similarity cache (that's Module 9 territory)

## Quick Recap

1. What's used as the cache key, and why does it need to be a hash rather than the raw text?
2. What two things prove a cache hit actually happened, without reading server logs?
3. Why does this cache have a TTL instead of lasting forever?

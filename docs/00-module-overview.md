# Module 17 – Production AI Engineering

**Duration:** 4 hrs
**Goal:** You've deployed things, triggered them, and watched them run. This module is the last mile: taking one small AI service and making it trustworthy enough for real, unpredictable internet traffic.

## The use case: ModeraAI — a content moderation bouncer

Think of it like hiring a bouncer for a comments section. Any site that accepts user text — a blog, a forum, a chat app — needs to check whether a piece of text is okay before it goes live. ModeraAI is that bouncer, built as one tiny standalone API with a single job:

```
POST /moderate
{"text": "I hate you, you're so stupid and ugly"}

-> {"flagged": true, "category": "harassment", "reasoning": "Insulting, demeaning language directed at a person."}
```
```
POST /moderate
{"text": "Great article, thanks for sharing!"}

-> {"flagged": false, "category": "safe", "reasoning": "Friendly, on-topic feedback."}
```

That's the entire product — one URL, send text, get a verdict, powered by one Gemini call underneath. **The point of this module isn't the bouncer itself — it's everything you'd have to do before trusting that bouncer with a real crowd.** Every topic below takes this same tiny service and hardens it against one specific real-world failure mode.

## Topics, and — critically — how each one is actually tested

| # | Topic | What we harden | How we test it |
|---|-------|-------------------|------------------|
| 1 | [Scaling](01-scaling.md) | Handling a burst of traffic | `scripts/load_test.py` fires 50 concurrent requests; count the instances that served them in the request logs |
| 2 | [Cloud Build](02-cloud-build.md) | Building the container reliably | `gcloud builds submit` run manually, then inspect the build log |
| 3 | [CI/CD](03-ci-cd.md) | Deploying automatically | Push a real commit to GitHub, watch a build+deploy happen with zero manual commands |
| 4 | [Versioning](04-versioning.md) | Knowing exactly what's live | Deploy `v2.0.0` alongside `v1.0.0`, call both by their distinct URLs/revisions |
| 5 | [Rollbacks](05-rollbacks.md) | Undoing a bad deploy | Prove v2 over-flags safe text, then roll live traffic back to v1 in one command |
| 6 | [Caching](06-caching.md) | Not re-paying for the same question | Call the same text twice, compare response time and `cache_hit` field |
| 7 | [Retry Strategies](07-retry-strategies.md) | Surviving a transient hiccup | A temporary revision whose Gemini calls always time out — watch the logs show each retry |
| 8 | [Timeouts](08-timeouts.md) | Never hanging forever | The same revision: the timed-out call ends in a clean 502 instead of hanging |
| 9 | [Rate Limiting](09-rate-limiting.md) | Surviving abuse | Fire requests past API Gateway's quota and expect a 429 (set up and counted, but no 429 seen on our run: see the topic) |
| 10 | [Cost Optimization](10-cost-optimization.md) | Not a surprise bill | Compare Flash vs. Pro cost, then prove caching cuts real Gemini calls with a request counter |

Every single topic in this module ends the same way: **break the thing on purpose, on your own terms, and watch the safeguard catch it** — the same discipline from Module 16, now applied to production resilience instead of monitoring.

## A quick note on topic 9

Rather than hand-building rate-limiting logic, this topic reuses **API Gateway's own built-in quota feature** (Module 15) — configured declaratively in the OpenAPI spec, not custom code. That's not a simplification for teaching purposes; it's the more realistic choice — real teams reach for the platform's built-in tool before writing custom rate-limiting code.

## How the pieces connect

```text
ModeraAI v1 (deployed by Cloud Build + CI/CD)
  ├──► Scaling (scripts/load_test.py) ───────────┐
  ├──► Caching + retries + timeouts (built in) ──┼──► Cost optimization (ties it all together)
  └──► API Gateway rate limiting ────────────────┘

ModeraAI v2 (stricter policy) ──► Rollback to v1
```

## Prerequisites before starting

- Modules 14, 15, and 16 complete
- A GitHub account with this course's repo (or your own fork) — needed for topic 3's CI/CD trigger
- `gcloud` and [`uv`](https://docs.astral.sh/uv/) installed
- The setup in [`commands.md`](../commands.md) section 0 done: `.env` filled in, the Python environment made with uv,
  and the one-time cloud resources created

Every command in these lessons, with the real values, is in [`commands.md`](../commands.md). The lessons explain the
idea; `commands.md` is what you run.

## What you'll be able to do after this module

Take any small, working AI service and systematically prove it can survive real traffic, real failures, real cost pressure, and real mistakes — the actual difference between a demo and something you'd trust with real users.

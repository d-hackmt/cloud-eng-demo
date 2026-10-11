# Teacher Plan — Module 17: Production AI Engineering

**Total time:** 4 hrs (240 min) — includes a 30 min buffer. This is the most operationally dense module in the course (10 topics); budget real time and don't rush topic 3 (CI/CD) or topic 9 (API Gateway quotas), both of which have fiddlier one-time setup.

## Before you start recording/teaching

- [ ] Modules 14-16 complete
- [ ] This repo pushed to GitHub (or your fork) — needed for topic 3
- [ ] Section 0 of [`commands.md`](../commands.md) done: `.env` filled in, the uv environment made, the one-time cloud resources created
- [ ] Run through the whole module once yourself first — topic 3's GitHub connection and topic 9's quota YAML are the two most likely places to hit a real snag
- [ ] Deploy ModeraAI v1 *before* recording so topic 1 doesn't waste camera time on a first deploy

## Suggested pacing (240 min)

| # | Topic | Minutes | Format |
|---|-------|---------|--------|
| 1 | Scaling | 25 | `scripts/load_test.py`, watch instances scale, then cap and re-run |
| 2 | Cloud Build | 20 | Manual `gcloud builds submit` |
| 3 | CI/CD | 30 | GitHub connection (one-time) + push-to-deploy demo |
| 4 | Versioning | 20 | Deploy v2 alongside v1 |
| 5 | Rollbacks | 25 | Prove v2 is bad, roll back traffic |
| 6 | Caching | 20 | Same text twice, compare timing |
| 7 | Retry Strategies | 20 | `simulate_transient_failure`, watch it recover |
| 8 | Timeouts | 20 | `simulate_hang`, watch it get cut off |
| 9 | Rate Limiting | 25 | API Gateway quota, watch a real 429 |
| 10 | Cost Optimization | 25 | Model cost comparison + caching's real savings |
| — | Buffer | 30 | — |

## Teaching order rationale

Keep the syllabus order — it's already well-sequenced: get the service deployed and scaling (1), automate how it gets built and shipped (2-3), learn to change it safely (4-5), then harden its actual request-handling behavior (6-9), closing with the topic that ties every cost lever together (10).

## Per-Component Focus

### 1. Scaling
**Land this one idea:** "Nobody scales infinitely for free — this is a dial, and topic 10 is about where you set it."
- Demo: run `scripts/load_test.py` (50 concurrent requests) and count the instances in the request logs. With the default concurrency (80 per instance) one instance takes all 50, so set `--concurrency=5` first to make scaling visible (10 instances). Then cap at `--max-instances=2` and run it again: 2 instances.
- Common confusion: students expect autoscaling to be limitless by default. It has a ceiling you set, on purpose.
- Don't rely on the Console's instance graph live: it lags by minutes.

### 2. Cloud Build
**Land this one idea:** "This is the exact same `docker build` + `docker push` from Module 14 — just running on Google's infrastructure instead of your laptop."
- Demo: `gcloud builds submit`, watch the build log stream, point out this is a real remote build, not local.

### 3. CI/CD
**Land this one idea:** "From here on, deploying is just: write code, push it, done."
- The GitHub connection is a one-time, Console-based step (same category as Module 11's OAuth consent screen) — walk through it carefully.
- Demo: make a trivial code change, commit, push, watch Cloud Build kick off automatically and deploy without a single manual `gcloud` command.
- Common confusion: expecting the trigger to fire instantly. There's a real delay between push and build start — don't fake it.

### 4. Versioning
**Land this one idea:** "`:latest` tells you nothing. `v2.0.0` tells you exactly what's running."
- Demo: build and tag v2 with a stricter moderation policy, deploy it as a distinct, addressable revision alongside v1.

### 5. Rollbacks
**Land this one idea:** "This is why versioning exists — undoing a bad decision should take one command, not a re-deploy from scratch."
- Demo: call v2 with an obviously-safe comment, show it gets incorrectly flagged (the deliberately-too-strict policy). Then roll Cloud Run traffic back to v1 with `update-traffic`, re-run the same call, show it now passes.
- Common confusion: thinking a rollback requires rebuilding v1. It doesn't — the v1 revision is already sitting there, ready to receive traffic again instantly.

### 6. Caching
**Land this one idea:** "Same input, same answer — why pay for the same Gemini call twice?"
- Demo: call the same text twice, show the `cache_hit: false` then `cache_hit: true`, and the dramatic timing difference.

### 7. Retry Strategies
**Land this one idea:** "A transient failure isn't a real failure if you retry through it — the caller never even knows it happened."
- Demo: `?simulate_transient_failure=true` fails the first two attempts on purpose, succeeds the third — show the retry attempts in the logs, and that the final response is still a clean success.

### 8. Timeouts
**Land this one idea:** "A slow failure is worse than a fast one — nobody should wait forever for an answer that's never coming."
- Demo: `?simulate_hang=true` stalls for 60 s. Cloud Run cuts it at 30 s with a 504. Then show the app's own Gemini timeout separately, with a temporary 1 ms setting: a clean 502.
- Be honest here: the hang switch is cut by Cloud Run's timeout, not the app's, because it sleeps before Gemini is called. Two safety nets, each tested on its own.

### 9. Rate Limiting
**Land this one idea:** "We didn't write a single line of rate-limiting code — API Gateway's quota does this declaratively."
- Demo: no key gives a 401, a key gives a 200, and Cloud Monitoring shows the requests counted against the limit of 10.
- Be honest here: on our run no request ever got a `429`, likely because the key and the API are in the same project. Proving the block needs a key from a second project. Don't promise the 429 on camera.
- Common confusion: expecting to see gateway rejections in ModeraAI's own logs. You won't — API Gateway answers them before ModeraAI sees the request.

### 10. Cost Optimization
**Land this one idea:** "Every lever in this module - caching, max-instances, model choice - is secretly a cost lever too."
- Demo: run the same moderation request through Flash and Pro, compare cost; then show a counter proving caching cut real Gemini calls roughly in half across a repeated test set.
- Close the module by explicitly listing which of the 9 earlier topics also doubles as a cost control.

## Wrap-up

- Rapid-fire recap: one question from each topic's "Quick Recap" (10 questions)
- Close with the module's throughline: every topic here answers "what could go wrong, and how do I prove I've handled it" — that's the actual job description of production engineering
- No "tease next module" — modules are being built out of order

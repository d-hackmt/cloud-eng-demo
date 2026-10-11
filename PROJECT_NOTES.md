# Module 17 — Project notes: ModeraAI in production

## What it is

ModeraAI is a content moderation API: send it a comment, get back whether it should be blocked.
It is a small Flask service on Cloud Run that asks Gemini (`gemini-2.5-flash`) for a verdict.

```
POST /moderate  {"text": "I hate you, you're so stupid and ugly"}
-> {"flagged": true, "category": "harassment", "reasoning": "...", "cache_hit": false, "policy": "standard"}
```

The service is the easy part. The module is about what you must add before trusting it with real
traffic. Every topic breaks it on purpose and shows the safeguard catching it. All ten were run for
real on `gcp-fde-project`. Nine are proven end to end; **topic 9 is only partly proven** (see below).

## The 10 topics at a glance, with what we measured

| # | Topic | What we saw |
|---|---|---|
| 1 | Scaling | 50 simultaneous requests: **1 instance** with Cloud Run's default (80 requests each), **10** with concurrency set to 5, **2** when capped at 2 |
| 2 | Cloud Build | build, push and deploy in **2 min 17 s** with one command |
| 3 | CI/CD | a `git push` built and deployed the service by itself in about 2.5 minutes; the live `/health` changed with no deploy command |
| 4 | Versioning | v2 (strict) deployed at **0% traffic** with its own URL; the same comment: v1 lets it through, v2 flags it |
| 5 | Rollbacks | v2 promoted, wrongly flags a safe comment; one command back to v1 in **9 seconds**, no rebuild |
| 6 | Caching | a real Gemini call took **2.9 s**; repeats took **0.46 s** |
| 7 | Retries | a request forced to fail twice took **6.4 s** against 2.4 s normally; the log shows both retries |
| 8 | Timeouts | a hang is cut at **30.4 s** by Cloud Run (504); a 1 ms Gemini timeout gives a clean 502 after 3 retries |
| 9 | Rate limiting | gateway, key and limit are in place and requests are counted, but **nothing was ever blocked** |
| 10 | Cost | caching cut 6 requests to 3 real Gemini calls; most Gemini tokens are hidden "thinking" |

## A tiny example of each, in plain words

The story is a blog's comment section using ModeraAI as its bouncer.

1. **Scaling.** A post goes viral and 50 people comment at once. Cloud Run starts extra copies of the service to cope,
   up to a ceiling you set. With the defaults, one copy handled all 50, so scaling never showed; we lowered how many
   requests one copy takes so it did.
2. **Cloud Build.** Instead of building the container on your laptop, one command has Google build it, store it and
   deploy it.
3. **CI/CD.** A developer pushes a change to GitHub and the new version is live minutes later with nobody typing a
   deploy command. A change to a file outside the service folder deliberately starts nothing.
4. **Versioning.** A stricter version 2 goes live next to version 1, with no visitors, and gets its own address so
   you can try it first.
5. **Rollbacks.** Version 2 goes live and starts blocking "I disagree with this policy." Moving traffic back to
   version 1 fixes it in seconds, with no rebuild.
6. **Caching.** The same comment is posted twice. The second answer comes from a saved copy: faster and free.
7. **Retries.** The Gemini call fails for a moment. The service waits a second, tries again, waits two, tries again,
   and succeeds. The customer just sees a slightly slower answer.
8. **Timeouts.** If Gemini stalls, the service gives up after 10 seconds and answers with an error. If the service
   itself stalls, Cloud Run cuts it off at 30 seconds. Nobody waits forever.
9. **Rate limiting.** A bot floods the API. A front door is meant to say "10 requests a minute per customer, then
   429". We set that up; see the next section.
10. **Cost.** Flash costs a fraction of Pro, caching avoids calls, and turning off Gemini's hidden thinking cut the
    tokens for one moderation request by about 80%.

## Topic 9 in one paragraph (partly proven)

The gateway asks for an API key (no key gives a 401), forwards good calls, and has a limit of 10 a minute registered.
Cloud Monitoring showed 15 requests counted in one minute against that limit. But 15 of 15 and then 40 of 40 requests
returned 200; none got a 429. The likely reason is that the key belongs to the same project as the API, and quotas
limit a *customer* project. Google's documentation did not confirm this. Proving it needs a key from a second project.

## A real project you could build with this: reviews for a candle shop

You run a small shop selling handmade candles, and customers can leave reviews. You don't want abusive or spam
reviews appearing on your product pages, so every new review is checked before it goes live:

```
Customer writes a review
  -> your shop website sends it to the checker
     -> the checker asks Gemini: "is this okay?"
        -> okay: publish it     not okay: hold it for you to look at
```

That checker is ModeraAI. Everything in this module is what you would do to keep it working once real customers use it.

| Topic | The real situation at the candle shop | What you would do |
|---|---|---|
| 1 Scaling | You send a sale email and 300 people leave reviews in an hour | Run the checker on Cloud Run with a maximum number of copies: a rush is handled, and a bug can't run up a huge bill |
| 2 Cloud Build | You are tired of building and uploading the app from your laptop | `gcloud builds submit`: Google builds and deploys it |
| 3 CI/CD | You fix a bug and forget to deploy it | Connect your GitHub repo, so pushing your code deploys it |
| 4 Versioning | You want a stricter spam rule but are not sure about it | Deploy version 2 with no visitors and try it on its private address first |
| 5 Rollbacks | The stricter version starts blocking honest reviews like "arrived late, but lovely" | One command sends everyone back to version 1 in seconds |
| 6 Caching | A spammer pastes the same fake review 200 times | Remember the answer per review: repeats are instant and free |
| 7 Retries | Gemini fails for one second and a customer's review errors out | Wait a moment and try again, so the customer never sees the hiccup |
| 8 Timeouts | Gemini gets slow | Give up after 10 seconds and publish the review as "pending", so checkout never freezes because of a review check |
| 9 Rate limiting | Someone points a script at your checker and floods it | An API Gateway in front, with a limit per caller (set up here, but not proven to block: see topic 9 above) |
| 10 Cost | The Gemini bill is bigger than expected | Use the cheaper model, cache, and turn off Gemini's extra "thinking" for a simple yes-or-no task (about 80% fewer tokens in our one test) |

How the pieces connect:

```
Your shop -> API Gateway (needs a key, limits requests) -> ModeraAI on Cloud Run -> Gemini
                                                                 |
                                                         Firestore (the cache)

You push code to GitHub -> Cloud Build -> deploys a new revision of ModeraAI
```

### How you would actually do it

1. **Build the checker:** one endpoint, text in and a verdict out. This is `moderaai/main.py`.
2. **Deploy it** to Cloud Run (topics 1 and 2).
3. **Automate deploys** from GitHub (topic 3).
4. **Add the protections in the code:** the cache, the retries and the timeouts (topics 6 to 8).
5. **Practise deploying safely:** the new version at 0% first, with a rollback ready (topics 4 and 5).
6. **Put the front door in** and give your shop its own key (topic 9).
7. **Check the cost** once real traffic arrives (topic 10).

### Where else the same ideas apply

None of this is specific to moderation. The same steps fit anything that calls an AI model or another service: a
support-ticket sorter, a document summariser, a chatbot backend, a receipt reader. If you build only three things for
a first real project, make them **caching, retries with a timeout, and rollbacks**: they protect you from the most
common problems, which are a repeated bill, a hiccup, and a bad release.

### What a real team would add

- **Login on the service.** Ours was public, which is fine for a demo but not for a real shop.
- **Tests** that run before anything deploys.
- **Alerts**, so you hear about a failing checker before your customers do.
- **A rate limit that is proven,** tested from a separate project first (see topic 9).

## Problems found in the course files, and what was done

| # | What went wrong when run for real | Fixed? |
|---|---|---|
| 1 | The cache key was the text only, so a verdict cached under v2 (strict) was served after rolling back to v1. The rollback would have looked like it did nothing. | yes: the policy is in the key |
| 2 | `/healthz` returns Google's own 404 on a `run.app` URL: Cloud Run reserves that path. | yes: renamed `/health` |
| 3 | 50 concurrent requests never scaled: one instance takes 80 by default. | yes: concurrency 5 in the run |
| 4 | `cloudbuild.yaml` pointed at `code/17-.../`, a layout this repo does not have. | yes |
| 5 | The trigger's build was rejected instantly: a build run as a service account must say where its logs go. | yes: `logging: CLOUD_LOGGING_ONLY` |
| 6 | `--tag=v2` is refused: tags need 3 characters. | yes: `v2-0-0` |
| 7 | The script says "check the logs for the 3 attempts", but nothing logged retries. | yes: one log line per retry |
| 8 | A rollback moves traffic, not settings. The service kept `MODERATION_POLICY=strict`, so the next plain deploy (or the CI/CD trigger) would ship the strict policy. | documented; deploy with explicit settings |
| 9 | API Gateway needs its own managed service enabled first; the script never does it. | documented |
| 10 | The script's API key is unrestricted. | yes: restricted to this API |
| 11 | `simulate_hang` is cut by Cloud Run's 30 s, never by the app's 10 s Gemini timeout. | documented; the app timeout tested separately |
| 12 | The cost demo's "output tokens" leaves out thinking tokens, about 80% of the total; its prices are illustrative. | documented |
| 13 | The GitHub connection for the trigger can't be created by command alone: one browser authorisation. | documented |

### Changes after the run (2026-10-11)

These were made after the teardown. They were tested locally (tests with stand-ins for Firestore and Gemini, real Gemini
calls, the image built and run with Docker), but **not yet deployed to Cloud Run**.

| Change | Why |
|---|---|
| The Dockerfile installs packages with **uv** (pinned 0.8.14) and runs the app as a normal user | faster builds; no root in the container |
| `cloudbuild.yaml`'s deploy sets the service account and every env var | fixes problem 8 for CI/CD: a push can no longer ship leftover settings |
| The failure switches need `ENABLE_DEMO_SWITCHES=true` | a real deploy can't be made to hang by a stranger |
| Texts over 5,000 characters get a 413; a body that isn't a JSON object gets a 400 instead of a 500 | caps the cost of one request; a JSON list used to crash the handler |
| The comment is sent to Gemini apart from the instructions | a comment can't easily give the model orders; a test "ignore your rules" comment was flagged, not obeyed |
| A failed moderation returns `{"error": "moderation failed"}`, with the details only in the logs | internal errors aren't shown to callers |
| `.gitignore` and `moderaai/.dockerignore` added | `.env` stays out of git, uploads and the image |
| `commands.md` rewritten with exact values and no placeholders, for bash on any OS (Git Bash on Windows) | usable directly as the replication reference |

## See it, and question it

The service was live at `https://moderaai-1039893753206.us-central1.run.app` during the run and was **deleted on
2026-09-20** (teardown is at the end of `commands.md`), so these commands no longer work. To try it again, redeploy
with the steps in `commands.md` (about 5 minutes for topics 1 and 2); the same commands then apply:

```bash
curl https://<your-service-url>/health
curl -X POST https://<your-service-url>/moderate -H "Content-Type: application/json" \
  -d '{"text": "Your comment here"}'
```

Try the same text twice (`cache_hit`), or add `?simulate_transient_failure=true` or `?simulate_hang=true`.

## Where to watch it in the Google Cloud Console

These are the standard Console pages, **not opened during this run** (everything was checked from the command
line). They are empty once the resources are deleted.

| What | Open this | You'll see |
|---|---|---|
| The service, its revisions and traffic split | https://console.cloud.google.com/run/detail/us-central1/moderaai/revisions?project=gcp-fde-project | which revision has what percent; the instance-count graph under Metrics lags by minutes |
| Builds | https://console.cloud.google.com/cloud-build/builds;region=us-central1?project=gcp-fde-project | every build, including the one the push started, and its log |
| The CI/CD trigger | https://console.cloud.google.com/cloud-build/triggers;region=us-central1?project=gcp-fde-project | `moderaai-deploy-trigger` |
| Container images | https://console.cloud.google.com/artifacts/docker/gcp-fde-project/us-central1/moderaai-repo?project=gcp-fde-project | the `v1.0.0`, `v2.0.0` and `latest` images |
| The cache | https://console.cloud.google.com/firestore/databases/-default-/data/panel/moderation_cache?project=gcp-fde-project | one document per (policy, text) with the verdict |
| The gateway | https://console.cloud.google.com/api-gateway?project=gcp-fde-project | the gateway, its config and the quota |
| Logs (retries, timeouts, gateway calls) | https://console.cloud.google.com/logs/query?project=gcp-fde-project | filter by `moderaai` |

## What it can't do (yet)

- **Protect itself from strangers.** Anyone with the URL can call it and cost you Gemini calls. There is no login.
- **Prove its rate limit.** See topic 9.
- **Count calls across instances.** `/stats` lives in each instance's memory and resets on a cold start; the cost
  demo is only reliable when one instance answers the whole run.
- **Test before it deploys.** The CI/CD trigger ships whatever is pushed to the branch, with no tests in between.
- **Keep old cache entries tidy.** Nothing deletes expired entries from Firestore; they just stop being used.
- **Tell you what a verdict is worth.** The verdicts are one model's opinion; nothing measures how often they are
  right, and the strict policy simply flags more.

## Good to know

- **Provisioning times.** Deploy from source about 3 minutes, Cloud Build 2 to 2.5 minutes, the API Gateway about
  **11 minutes** (the slowest step).
- **Cost.** Everything used stays inside free tiers; the only spend is the Gemini calls. Nothing bills by the hour.
- **The build source.** `gcloud builds submit` from the repo root uploads the whole repo; check what goes with
  `gcloud meta list-files-for-upload .` first. `.env` and tokens are excluded by `.gitignore`.
- **Keys in logs.** The gateway's log entry has the raw API key in `jsonPayload.api_key`. Leave it out of queries.
- **Line endings.** `.env`, `.env.example` and the requirements files need Unix (LF) line endings (they have them
  now); leave the `.bat` files with Windows (CRLF) endings.

## Links

- Repository: https://github.com/d-hackmt/cloud-eng-demo (branch `main`; the CI/CD trigger in `commands.md` watches it)
- Where the original 2026-09-20 run lived: https://github.com/AnjaniMalhotra/gcp-modules/tree/17-production-ai-engineering
- Every command, with real values: [`commands.md`](commands.md)

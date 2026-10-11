# Code — Module 17: Production AI Engineering

One small, self-contained Flask service, **ModeraAI** (a content moderation API), hardened topic by topic against real production failure modes: bursty traffic, unreliable dependencies, hangs, abuse, and cost blowups. It uses no code from any other module.

**Scope note:** the service is deployed `--allow-unauthenticated`, so anyone with its URL can call it (and cause Gemini calls). That keeps every topic testable with a plain `curl`, but delete the service when you finish.

## Layout

```
cloud-eng-demo/                (https://github.com/d-hackmt/cloud-eng-demo)
├── moderaai/                  the service: main.py, Dockerfile (installs with uv), requirements.txt,
│                              cloudbuild.yaml, .dockerignore, and static/index.html (the web page at /)
│                              (keep this path: the CI/CD trigger and cloudbuild.yaml point at it)
├── scripts/
│   ├── load_test.py           fires N concurrent requests (topics 1 and 9)
│   └── cost_comparison_demo.py  Flash vs Pro tokens, and what caching saves (topic 10)
├── gateway/
│   └── openapi_spec.yaml      the API Gateway definition with the 10-requests-a-minute quota
├── docs/                      the lessons: one file per topic
├── bat-files/                 the original Windows .bat scripts, kept for reference
├── commands.md                every gcloud command run, with real values, and what each showed
├── PROJECT_NOTES.md           what was found, what it can't do, where to look in the Console
├── requirements.txt           for the two scripts
├── .gitignore                 keeps .env and .venv out of git and out of build uploads
└── .env.example
```

The scripts and the gateway spec were moved into `scripts/` and `gateway/` after the run, to tidy the folder. The
`.bat` files in `bat-files/` are the unchanged originals, so they still use the old locations.

## The ten topics

| # | Topic | What you do | Run with |
|---|---|---|---|
| 1 | Scaling | 50 concurrent requests, count the instances, then cap them | `scripts/load_test.py` |
| 2 | Cloud Build | build, push and deploy with one remote command | `gcloud builds submit` |
| 3 | CI/CD | a push to GitHub deploys the service by itself | a Cloud Build trigger |
| 4 | Versioning | deploy v2 next to v1 at 0% traffic | `gcloud run deploy --no-traffic --tag` |
| 5 | Rollbacks | promote v2, see it wrongly flag safe text, roll back to v1 | `gcloud run services update-traffic` |
| 6 | Caching | the same text twice: the second answer is instant | built into `main.py` |
| 7 | Retries | `?simulate_transient_failure=true` fails twice, then succeeds | built into `main.py` |
| 8 | Timeouts | `?simulate_hang=true` stalls and gets cut off | built into `main.py` |
| 9 | Rate limiting | API Gateway limits each project to 10 requests a minute | `gateway/openapi_spec.yaml` |
| 10 | Cost | Flash against Pro, and how many Gemini calls caching avoids | `scripts/cost_comparison_demo.py` |

## Try it in a browser

The service has a simple web page at its root URL (`/`): type a comment, press **Check comment**, and see the verdict,
the reasoning, whether it came from the cache, and how long it took. It can also turn on the two failure switches
(topics 7 and 8). It's one HTML file, `moderaai/static/index.html`, that calls the same `/moderate` API as `curl`.

- Locally: http://localhost:8080 (see the local container run in `commands.md`)
- On Cloud Run: https://moderaai-1039893753206.us-central1.run.app

## Setup

All the infrastructure is created with `gcloud`: see [`commands.md`](commands.md), which has every command with the real values, ready to paste (bash: Git Bash on Windows, or any macOS/Linux terminal). The `.bat` scripts in `bat-files/` are the Windows-only originals, kept for reference.

The local Python environment is made with [uv](https://docs.astral.sh/uv/), a fast replacement for `pip` and `venv`:

```bash
uv venv --python 3.12 .venv                                       # same Python as the container
uv pip install -r requirements.txt -r moderaai/requirements.txt   # the scripts' and the service's packages
gcloud auth application-default login
set -a && source .env && set +a
uv run python scripts/load_test.py --help                         # uv run uses .venv on any OS
```

**Line endings.** `.env`, `.env.example` and the requirements files must have Unix (LF) line endings, or `source .env` leaves a hidden character on every value. They do now. The `.bat` files must keep their Windows (CRLF) endings.

## Settings and secrets

The service has **no secrets**: it calls Gemini and Firestore as its own service account (`moderaai-sa`), so there is no password or key to store. Its settings (`PROJECT_ID`, `MODERATION_POLICY`, ...) are ordinary configuration, given to Cloud Run with `--set-env-vars` at deploy time.

- **Secret Manager** is the right home for a real secret (say, a third-party API key the service had to send). Nothing here needs it yet.
- **A `.env` file inside the image** would be the wrong choice: anyone who can pull the image could read it, and every change would mean a rebuild. `moderaai/.dockerignore` keeps `.env` out of the image.
- **For a local container run**, pass the existing `.env` at run time with `docker run --env-file .env` (see `commands.md`, section 0). Nothing extra to maintain.

The one real secret in this module is the API Gateway key (topic 9). It belongs to the *caller*, not the service, so it stays in the gitignored `.env`.

## Security (it's a demo, but the basics are covered)

| Risk | What's in place |
|---|---|
| Anyone with the URL can call the service | Accepted for the demo (`--allow-unauthenticated`); delete the service when done. Topic 9's gateway is the front door with a key. |
| The failure switches could be used to tie up the service | `?simulate_hang` and `?simulate_transient_failure` only work when `ENABLE_DEMO_SWITCHES=true`; it is off unless set |
| Huge texts running up the Gemini bill | Texts over 5,000 characters are refused (HTTP 413) |
| A comment that tries to give the model orders ("ignore your rules...") | The text is sent apart from the instructions, and the model is told to judge it, not obey it |
| Internal errors shown to callers | Callers get `{"error": "moderation failed"}`; the details go to the logs |
| The app running as root in the container | The Dockerfile switches to a normal user |
| `.env` leaking into git, uploads or the image | `.gitignore` and `moderaai/.dockerignore` |

## Run order

Follow [`commands.md`](commands.md); the order matters:

1. Setup: the Artifact Registry repo, the Firestore database, the `moderaai-sa` service account and its two roles.
2. Topic 1: deploy v1 and load-test. The service URL is known in advance (`https://moderaai-1039893753206.us-central1.run.app`) and is already in `.env`.
3. Topic 2: the manual Cloud Build, run from the **repo root**.
4. Topic 3: needs your GitHub account: a one-time browser authorisation, then the trigger and a real push.
5. Topics 4 and 5: v2 and the rollback. The service's *settings* stay at whatever the last deploy set, so deploy with `MODERATION_POLICY` set explicitly afterwards.
6. Topics 6 to 8: `curl` calls against the service.
7. Topic 9: put the real service URL in `gateway/openapi_spec.yaml`, create the gateway (about 11 minutes), then the API key, which is restricted to this API.
8. Topic 10: `uv run python scripts/cost_comparison_demo.py`.
9. Teardown, at the end of `commands.md`.

## What was changed from the course files

The service and scripts were corrected where running them for real showed a problem: the cache key ignored the moderation policy (which made the rollback demo look like it did nothing), `/healthz` is reserved by Cloud Run, retries were never logged, the build paths assumed a different repo layout, and a few scripts had wrong flags. The full list, with what each one looked like when it went wrong, is in [`PROJECT_NOTES.md`](PROJECT_NOTES.md).

Later (2026-10-11): the Dockerfile installs with uv and runs as a normal user, `cloudbuild.yaml` sets every setting on deploy, and the security basics above were added. `main.py` was checked with local tests and real Gemini calls, and the image was built and run locally. The changed service hasn't been deployed to Cloud Run yet.

## Cost note

Cloud Run, Cloud Build, Artifact Registry, Firestore and API Gateway all stay inside their free tiers for this module's load. The only real spend is the Gemini calls, kept small by the module's own caching. Nothing here bills by the hour the way Redis and Cloud SQL do, but the public service is still worth deleting when you finish.

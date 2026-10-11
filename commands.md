# Module 17 — GCP CLI Commands

Every step of this module as copy-paste commands with the real values filled in. Run them top to bottom.
The original run was on 2026-09-20; the results it recorded are kept as `# ->` comments.

**Shell.** Bash. On Windows use **Git Bash** (it comes with Git for Windows); macOS, Linux and Cloud Shell work as
they are. The Windows `.bat` originals are in [`bat-files/`](bat-files/) for reference only.

**Run each topic in one terminal window.** A few commands save a value in a variable (like `$V1_REVISION`) that a
later command in the same topic uses. Google generates some names itself (revision names, the gateway's address,
the API's managed service name); the commands look those up for you, so there is nothing to edit.

```
Project ID:     gcp-fde-project
Project number: 1039893753206
Region:         us-central1
Service URL:    https://moderaai-1039893753206.us-central1.run.app   (fixed: service name + project number + region)
GitHub repo:    https://github.com/d-hackmt/cloud-eng-demo  (branch main)
```

**Folder layout.** Every command runs from the repo root (the folder with this file). `moderaai/cloudbuild.yaml` and
the CI/CD trigger point at `moderaai/`. To start from a fresh copy:

```bash
git clone https://github.com/d-hackmt/cloud-eng-demo.git
cd cloud-eng-demo
```

The original 2026-09-20 run used a different repo (`AnjaniMalhotra/gcp-modules`, where this module sat in a
`17-production-ai-engineering/` subfolder). The commands below are for this repo.

---

## 0. Setup

### Tools and login

```bash
gcloud --version        # Google Cloud CLI
uv --version            # Python package manager (install: https://docs.astral.sh/uv/getting-started/installation/)
docker --version        # only for the optional local container run below

gcloud auth login
gcloud config set project gcp-fde-project
gcloud auth application-default login   # lets the local Python scripts call Gemini and Firestore
```

### APIs

Enable everything the module uses (already-enabled APIs are skipped), then check:

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  firestore.googleapis.com aiplatform.googleapis.com apigateway.googleapis.com servicemanagement.googleapis.com \
  servicecontrol.googleapis.com apikeys.googleapis.com secretmanager.googleapis.com --project=gcp-fde-project

gcloud services list --enabled --project=gcp-fde-project --format="value(config.name)" \
  | grep -E "^(run|cloudbuild|artifactregistry|firestore|aiplatform|apigateway|servicemanagement|servicecontrol|apikeys|secretmanager)\."
# -> the 10 APIs above
```

### `.env`

`.env` holds the settings for the local scripts. It is gitignored and never goes into the container image. Create it
from the example and fill in the values (skip the first two lines if `.env` already has them):

```bash
cp .env.example .env
sed -i.bak -e 's|^PROJECT_ID=.*|PROJECT_ID=gcp-fde-project|' \
  -e 's|^GITHUB_USERNAME=.*|GITHUB_USERNAME=d-hackmt|' \
  -e 's|^SERVICE_URL=.*|SERVICE_URL=https://moderaai-1039893753206.us-central1.run.app|' .env && rm .env.bak

set -a && source .env && set +a        # loads .env into this terminal; repeat in every new terminal
```

### Python environment (uv)

One virtual environment for the scripts and for running the service locally. `uv run` always uses this `.venv`, so
the same command works on Windows, macOS and Linux:

```bash
uv venv --python 3.12 .venv
uv pip install -r requirements.txt -r moderaai/requirements.txt
uv run python -c "import flask, google.genai, google.cloud.firestore, tenacity; print('ok')"
# -> ok
```

### One-time cloud resources

```bash
gcloud artifacts repositories create moderaai-repo --project=gcp-fde-project \
  --repository-format=docker --location=us-central1 --description="Container images for ModeraAI (Module 17)"

gcloud firestore databases create --project=gcp-fde-project --location=us-central1 --type=firestore-native

gcloud iam service-accounts create moderaai-sa --project=gcp-fde-project --display-name="ModeraAI Runtime SA"

# least privilege for the service itself: call Gemini, and read/write Firestore
gcloud projects add-iam-policy-binding gcp-fde-project \
  --member="serviceAccount:moderaai-sa@gcp-fde-project.iam.gserviceaccount.com" --role="roles/aiplatform.user" --condition=None
gcloud projects add-iam-policy-binding gcp-fde-project \
  --member="serviceAccount:moderaai-sa@gcp-fde-project.iam.gserviceaccount.com" --role="roles/datastore.user" --condition=None

# let Cloud Build (which runs as the default compute service account) deploy the service as moderaai-sa
gcloud iam service-accounts add-iam-policy-binding moderaai-sa@gcp-fde-project.iam.gserviceaccount.com \
  --project=gcp-fde-project \
  --member="serviceAccount:1039893753206-compute@developer.gserviceaccount.com" --role="roles/iam.serviceAccountUser"
```

The last command was not in the original run, where it worked without it. It is there because `cloudbuild.yaml` now
names the service account explicitly. Running it when it isn't needed does no harm.

### Settings and secrets: how they reach the service

The service has **no secrets**. It reaches Gemini and Firestore as its service account (`moderaai-sa`), so there is
no password or key to store. Its settings (`PROJECT_ID`, `MODERATION_POLICY`, ...) are plain configuration, passed
with `--set-env-vars` at deploy time. Secret Manager is for real secrets; use it the day the service needs one, for
example a third-party API key. Settings are never baked into the image (`moderaai/.dockerignore` keeps `.env` out).
For a local container run, the same `.env` is passed in at run time with `--env-file`, as shown next.

### Optional: run the container on your laptop

Needs Docker running and the setup above (Firestore must exist for `/moderate`). Your own Google login is mounted in
read-only, so the container can call Gemini and Firestore as you:

```bash
docker build -t moderaai:local moderaai

# Windows (Git Bash). MSYS_NO_PATHCONV stops Git Bash from rewriting the /tmp paths.
MSYS_NO_PATHCONV=1 docker run -d --rm --name moderaai-local -p 8080:8080 --env-file .env \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json \
  -v "$APPDATA/gcloud/application_default_credentials.json:/tmp/adc.json:ro" moderaai:local

# macOS / Linux: the same, with the login file at ~/.config/gcloud/
# docker run -d --rm --name moderaai-local -p 8080:8080 --env-file .env \
#   -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json \
#   -v "$HOME/.config/gcloud/application_default_credentials.json:/tmp/adc.json:ro" moderaai:local

curl http://localhost:8080/health
# -> {"policy":"standard","service":"moderaai","status":"ok"}
curl -X POST http://localhost:8080/moderate -H "Content-Type: application/json" -d '{"text": "Great article, thanks for sharing!"}'

# or use the web page: open http://localhost:8080 in a browser

docker logs -f moderaai-local      # watch the logs (Ctrl+C to stop watching)
docker stop moderaai-local
```

---

## Topic 1 — Scaling

Deploy v1. Takes about 3 minutes, including the image build:

```bash
gcloud run deploy moderaai --source moderaai --project=gcp-fde-project --region=us-central1 \
  --allow-unauthenticated \
  --service-account=moderaai-sa@gcp-fde-project.iam.gserviceaccount.com \
  --set-env-vars=PROJECT_ID=gcp-fde-project,LOCATION=us-central1,MODERATION_POLICY=standard,MODEL_NAME=gemini-2.5-flash,GEMINI_TIMEOUT_MS=10000,CACHE_TTL_SECONDS=3600,ENABLE_DEMO_SWITCHES=true \
  --max-instances=10 --timeout=30 --quiet
# -> Service URL: https://moderaai-1039893753206.us-central1.run.app
```

Google also creates a second Artifact Registry repo, `cloud-run-source-deploy`, for the source build. The teardown
removes it.

```bash
curl https://moderaai-1039893753206.us-central1.run.app/health
# -> {"policy":"standard","service":"moderaai","status":"ok"}
curl -X POST https://moderaai-1039893753206.us-central1.run.app/moderate -H "Content-Type: application/json" \
  -d '{"text": "I hate you, you are so stupid and ugly"}'
# -> {"cache_hit":false,"category":"harassment","flagged":true,"policy":"standard", ...}
```

`/health`, not `/healthz`: Cloud Run reserves `/healthz` on `run.app` addresses and answers it with its own 404.

The same checks in a browser: open https://moderaai-1039893753206.us-central1.run.app (the web page at `/`).

### Load test, and count the instances

Each run: note the start time, fire 50 requests at once, then count which instances served them. The request logs
take up to a minute to appear, so wait a moment before the count. The Console's instance graph lags by minutes.

```bash
# Run 1: Cloud Run's default concurrency (80 requests per instance)
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
uv run python scripts/load_test.py --url https://moderaai-1039893753206.us-central1.run.app --requests 50
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=moderaai AND httpRequest.requestMethod=POST AND timestamp>=\"$START\"" \
  --project=gcp-fde-project --limit=200 --format="value(labels.instanceId)" | sort | uniq -c
# -> 1 instance served all 50

# Run 2: at most 5 requests per instance, so 50 requests need more instances
gcloud run services update moderaai --project=gcp-fde-project --region=us-central1 --concurrency=5 --quiet
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
uv run python scripts/load_test.py --url https://moderaai-1039893753206.us-central1.run.app --requests 50
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=moderaai AND httpRequest.requestMethod=POST AND timestamp>=\"$START\"" \
  --project=gcp-fde-project --limit=200 --format="value(labels.instanceId)" | sort | uniq -c
# -> 10 instances (5 to 7 requests each)

# Run 3: cap the service at 2 instances
gcloud run services update moderaai --project=gcp-fde-project --region=us-central1 --max-instances=2 --quiet
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
uv run python scripts/load_test.py --url https://moderaai-1039893753206.us-central1.run.app --requests 50
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=moderaai AND httpRequest.requestMethod=POST AND timestamp>=\"$START\"" \
  --project=gcp-fde-project --limit=200 --format="value(labels.instanceId)" | sort | uniq -c
# -> 2 instances

# put the ceiling back
gcloud run services update moderaai --project=gcp-fde-project --region=us-central1 --max-instances=10 --quiet
```

| Run | max-instances | concurrency | Instances that served the 50 requests | Wall time (recorded) |
|---|---|---|---|---|
| 1 | 10 | 80 (default) | **1** | 8.6 s |
| 2 | 10 | 5 | **10** | 10.8 s |
| 3 | 2 | 5 | **2** | 9.8 s |

The instance count proves the ceiling. The wall time barely changes, because the Gemini call dominates and extra
requests just queue.

---

## Topic 2 — Cloud Build (build, push and deploy with one command)

Run from the **repo root**, because that is also what the topic 3 trigger checks out. First, check exactly which
files would be uploaded as build source (`.env`, `.venv` and tokens must not be in the list; `.gitignore` keeps
them out):

```bash
gcloud meta list-files-for-upload .
```

Build, push and deploy. Took 2 min 17 s:

```bash
gcloud builds submit --project=gcp-fde-project \
  --config=moderaai/cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_TAG=v1.0.0 .
# -> a new moderaai revision, 100% of traffic
```

The build has three steps: `docker build` (the Dockerfile installs packages with **uv**), `docker push` to Artifact
Registry, and `gcloud run deploy`. The deploy step sets the service account and every env var itself, so it no longer
depends on what the service had before. It prints one harmless warning, `Setting IAM policy failed`: the build's
service account may not change who can call the service, and the service is already public from topic 1.

Check what the build left behind:

```bash
gcloud builds list --project=gcp-fde-project --limit=3
gcloud artifacts docker images list us-central1-docker.pkg.dev/gcp-fde-project/moderaai-repo --include-tags
# -> moderaai   v1.0.0
gcloud run services describe moderaai --region=us-central1 --project=gcp-fde-project
# -> concurrency 5, max 10 instances, moderaai-sa, 7 env vars
gcloud run services get-iam-policy moderaai --region=us-central1 --project=gcp-fde-project
# -> allUsers has roles/run.invoker
curl https://moderaai-1039893753206.us-central1.run.app/health
# -> {"policy":"standard","service":"moderaai","status":"ok"}
```

---

## Topic 3 — CI/CD (push to GitHub, it deploys itself)

Everything is a command except one browser authorisation in step 2.

**1. Let Cloud Build keep GitHub's token in Secret Manager.** Without this the connection fails with
`could not assert Secret Manager permissions`:

```bash
gcloud services enable secretmanager.googleapis.com --project=gcp-fde-project
gcloud projects add-iam-policy-binding gcp-fde-project \
  --member="serviceAccount:service-1039893753206@gcp-sa-cloudbuild.iam.gserviceaccount.com" \
  --role="roles/secretmanager.admin" --condition=None
```

**2. Create the GitHub connection.** It stays `PENDING_USER_OAUTH` and prints a link. Open the link in a browser
signed in to the Google account that owns the project, authorise GitHub as the repo owner (`d-hackmt`), and
install the Cloud Build GitHub App on the `cloud-eng-demo` repo. Then check:

```bash
gcloud builds connections create github moderaai-github --region=us-central1 --project=gcp-fde-project
# ...open the printed link and finish the authorisation in the browser...
gcloud builds connections describe moderaai-github --region=us-central1 --project=gcp-fde-project
# -> installationState: stage: COMPLETE
```

**3. Link the repo and create the trigger.** It watches only this branch and only changes under `moderaai/`:

```bash
gcloud builds repositories create cloud-eng-demo --remote-uri=https://github.com/d-hackmt/cloud-eng-demo.git \
  --connection=moderaai-github --region=us-central1 --project=gcp-fde-project

gcloud builds triggers create github --name=moderaai-deploy-trigger --region=us-central1 --project=gcp-fde-project \
  --repository=projects/gcp-fde-project/locations/us-central1/connections/moderaai-github/repositories/cloud-eng-demo \
  --branch-pattern='^main$' \
  --build-config=moderaai/cloudbuild.yaml \
  --included-files='moderaai/**' \
  --service-account=projects/gcp-fde-project/serviceAccounts/1039893753206-compute@developer.gserviceaccount.com
```

**4. Test it with a real push.** Any change under `moderaai/` triggers it. This one adds a small text file (the
Dockerfile copies only `main.py` and `static/`, so the file doesn't end up in the image):

```bash
date -u > moderaai/last-ci-test.txt
git add moderaai/last-ci-test.txt
git commit -m "test: trigger CI/CD"
git push origin main

gcloud builds list --region=us-central1 --project=gcp-fde-project --limit=1
# -> a new build, started by the trigger within seconds
gcloud builds log --stream $(gcloud builds list --region=us-central1 --project=gcp-fde-project --limit=1 --format="value(id)") \
  --region=us-central1 --project=gcp-fde-project
# -> about 2.5 minutes, SUCCESS
gcloud run revisions list --service=moderaai --region=us-central1 --project=gcp-fde-project --limit=3
# -> a new revision at the top, created with no deploy command
```

`moderaai/cloudbuild.yaml` ends with `options: logging: CLOUD_LOGGING_ONLY`. A build that runs as a specific service
account (as the trigger's does) is rejected instantly without it.

---

## Topic 4 — Versioning (v2 next to v1, at 0% of traffic)

First note which revision is v1, for the rollback in topic 5:

```bash
V1_REVISION=$(gcloud run services describe moderaai --region=us-central1 --project=gcp-fde-project \
  --format="value(status.latestReadyRevisionName)")
echo "v1 is $V1_REVISION"
```

Build and tag the v2 image (37 s), then deploy it as a revision that gets **no traffic** but has its own address.
"v2" is the same code with `MODERATION_POLICY=strict`:

```bash
gcloud builds submit moderaai --project=gcp-fde-project \
  --tag=us-central1-docker.pkg.dev/gcp-fde-project/moderaai-repo/moderaai:v2.0.0

gcloud run deploy moderaai --project=gcp-fde-project --region=us-central1 \
  --image=us-central1-docker.pkg.dev/gcp-fde-project/moderaai-repo/moderaai:v2.0.0 \
  --service-account=moderaai-sa@gcp-fde-project.iam.gserviceaccount.com \
  --set-env-vars=PROJECT_ID=gcp-fde-project,LOCATION=us-central1,MODERATION_POLICY=strict,MODEL_NAME=gemini-2.5-flash,GEMINI_TIMEOUT_MS=10000,CACHE_TTL_SECONDS=3600,ENABLE_DEMO_SWITCHES=true \
  --no-traffic --tag=v2-0-0 --quiet
# -> 0 percent of traffic
# -> reachable directly at https://v2-0-0---moderaai-mewtpyvzkq-uc.a.run.app

gcloud run services describe moderaai --region=us-central1 --project=gcp-fde-project --format="yaml(status.traffic)"
# -> v1 at 100%, and the v2-0-0 tag with its URL (if it differs from the one above, use this one)
```

The tag must be at least 3 characters: `--tag=v2` is refused, `v2-0-0` works.

The same comment, sent to each version:

```bash
curl -X POST https://moderaai-1039893753206.us-central1.run.app/moderate -H "Content-Type: application/json" \
  -d '{"text": "I disagree with this policy."}'
# -> v1: flagged: false, policy: standard

curl -X POST https://v2-0-0---moderaai-mewtpyvzkq-uc.a.run.app/moderate -H "Content-Type: application/json" \
  -d '{"text": "I disagree with this policy."}'
# -> v2: flagged: true, policy: strict
```

---

## Topic 5 — Rollbacks

Run in the same terminal as topic 4 (it uses `$V1_REVISION`):

```bash
# 1. ship v2 to everyone
gcloud run services update-traffic moderaai --region=us-central1 --project=gcp-fde-project --to-latest
# -> the v2 revision at 100%

# 2. the same mild comment is now wrongly flagged
curl -X POST https://moderaai-1039893753206.us-central1.run.app/moderate -H "Content-Type: application/json" \
  -d '{"text": "I disagree with this policy."}'
# -> flagged: true, policy: strict

# 3. roll back: one command, no rebuild (took 9 seconds)
gcloud run services update-traffic moderaai --region=us-central1 --project=gcp-fde-project \
  --to-revisions=$V1_REVISION=100

# 4. the same comment again
curl -X POST https://moderaai-1039893753206.us-central1.run.app/moderate -H "Content-Type: application/json" \
  -d '{"text": "I disagree with this policy."}'
# -> flagged: false, policy: standard
```

Steps 2 and 4 are both cache hits, and each returns its own policy's verdict, because the policy is part of the
cache key.

### Put the settings back

A rollback moves **traffic**, not **settings**. The service's settings still say `MODERATION_POLICY=strict` (from the
v2 deploy), and the next `gcloud run services update` would start from them. Make a new revision with the standard
policy and send traffic to it:

```bash
gcloud run services update moderaai --region=us-central1 --project=gcp-fde-project \
  --update-env-vars=MODERATION_POLICY=standard --quiet
gcloud run services update-traffic moderaai --region=us-central1 --project=gcp-fde-project --to-latest
curl https://moderaai-1039893753206.us-central1.run.app/health
# -> {"policy":"standard","service":"moderaai","status":"ok"}
```

---

## Topic 6 — Caching

Built into `moderaai/main.py`: each (policy, text) verdict is saved in Firestore for an hour. The same text three times:

```bash
curl -w "\nTime: %{time_total}s\n" -X POST https://moderaai-1039893753206.us-central1.run.app/moderate \
  -H "Content-Type: application/json" -d '{"text": "Nice write-up, I learned a lot from it"}'
# -> call 1: cache_hit false, 2.92 s (a real Gemini call)
# -> call 2: cache_hit true,  0.46 s
# -> call 3: cache_hit true,  0.46 s
```

The key is a hash of the policy plus the trimmed, lower-cased text, so `"  GREAT ARTICLE  "` and `"great article"`
share an entry. A first call can already be a hit if the text was sent before.

Look at the cache itself (`gcloud` has no command to read Firestore documents):

```bash
uv run python -c "
from google.cloud import firestore
for d in firestore.Client(project='gcp-fde-project').collection('moderation_cache').stream():
    print(d.id[:12], d.to_dict()['flagged'], d.to_dict()['category'])"
```

---

## Topic 7 — Retry strategies

`?simulate_transient_failure=true` makes the Gemini call fail twice, then succeed. It works only because the service
was deployed with `ENABLE_DEMO_SWITCHES=true`. The service retries with `tenacity`: 3 attempts, waiting 1 s, then 2 s.

```bash
curl -w "\nTime: %{time_total}s\n" -X POST "https://moderaai-1039893753206.us-central1.run.app/moderate?simulate_transient_failure=true" \
  -H "Content-Type: application/json" -d '{"text": "retry demo text"}'
# -> 200 after 6.35 s, against 2.36 s for a normal request: about 3 s of waiting between attempts
```

Each retry writes one log line:

```bash
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=moderaai AND textPayload:"Retrying"' \
  --project=gcp-fde-project --limit=10 --order=asc --format="value(timestamp,textPayload)"
# -> WARNING:moderaai:Retrying main.call_gemini in 1 seconds as it raised ConnectionError: Simulated transient failure (attempt 1).
# -> WARNING:moderaai:Retrying main.call_gemini in 2 seconds as it raised ConnectionError: Simulated transient failure (attempt 2).
```

---

## Topic 8 — Timeouts

`?simulate_hang=true` makes the handler sleep 60 seconds (also needs `ENABLE_DEMO_SWITCHES=true`):

```bash
curl -w "\nHTTP %{http_code} after %{time_total}s\n" -X POST "https://moderaai-1039893753206.us-central1.run.app/moderate?simulate_hang=true" \
  -H "Content-Type: application/json" -d '{"text": "timeout demo text"}'
# -> HTTP 504 after 30.4 s, body "upstream request timeout"
```

That is **Cloud Run's** request timeout (`--timeout=30`) cutting it off. The app's own 10-second Gemini timeout never
comes into play, because the switch sleeps before Gemini is called.

To test the app's Gemini timeout for real, deploy a temporary revision with a 1 ms timeout, at 0% traffic with its own
address, call it, then put everything back:

```bash
gcloud run services update moderaai --region=us-central1 --project=gcp-fde-project \
  --update-env-vars=GEMINI_TIMEOUT_MS=1 --no-traffic --tag=timeout-test --quiet

curl -w "\nHTTP %{http_code} after %{time_total}s\n" -X POST https://timeout-test---moderaai-mewtpyvzkq-uc.a.run.app/moderate \
  -H "Content-Type: application/json" -d '{"text": "gemini timeout test"}'
# -> {"error":"moderation failed"}  HTTP 502 (about 14 s including a cold start)

# the caller gets only a plain message; the real error is in the logs
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=moderaai AND (textPayload:"moderation failed" OR textPayload:"Timeout")' \
  --project=gcp-fde-project --limit=10 --format="value(timestamp,textPayload)"
# -> ... ConnectTimeout ... / ERROR:moderaai:moderation failed

# restore, so the 1 ms setting does not leak into later deploys
gcloud run services update moderaai --region=us-central1 --project=gcp-fde-project \
  --update-env-vars=GEMINI_TIMEOUT_MS=10000 --no-traffic --quiet
gcloud run services update-traffic moderaai --region=us-central1 --project=gcp-fde-project --to-latest --remove-tags=timeout-test
```

Two safety nets: the app times out the Gemini call and returns a clean 502 after its retries, and Cloud Run cuts
anything that runs past 30 seconds with a 504.

---

## Topic 9 — Rate limiting with API Gateway (partly proven)

**Result in one line:** the gateway, the API key and the 10-requests-a-minute limit all work as configured and the
requests are counted, but **no request was ever rejected with a 429** on the original run.

`gateway/openapi_spec.yaml` already points at `https://moderaai-1039893753206.us-central1.run.app`. Create the API
and its config:

```bash
gcloud api-gateway apis create moderaai-api --project=gcp-fde-project

gcloud api-gateway api-configs create moderaai-config --api=moderaai-api --openapi-spec=gateway/openapi_spec.yaml \
  --backend-auth-service-account=moderaai-sa@gcp-fde-project.iam.gserviceaccount.com --project=gcp-fde-project
```

The API gets its own Google-managed service, which must be enabled before the key and the quota work (the course
script leaves this out):

```bash
MANAGED_SERVICE=$(gcloud api-gateway apis describe moderaai-api --project=gcp-fde-project --format="value(managedService)")
echo $MANAGED_SERVICE
# -> moderaai-api-<random>.apigateway.gcp-fde-project.cloud.goog
gcloud services enable "$MANAGED_SERVICE" --project=gcp-fde-project
```

Create the gateway. This is the slowest step of the module (10 min 41 s on the original run). Save its address in
`.env`:

```bash
gcloud api-gateway gateways create moderaai-gateway --api=moderaai-api --api-config=moderaai-config \
  --location=us-central1 --project=gcp-fde-project

GATEWAY_URL="https://$(gcloud api-gateway gateways describe moderaai-gateway --location=us-central1 \
  --project=gcp-fde-project --format="value(defaultHostname)")"
echo $GATEWAY_URL
sed -i.bak "s|^GATEWAY_URL=.*|GATEWAY_URL=$GATEWAY_URL|" .env && rm .env.bak
```

Create an API key that works **only with this API**. The key goes straight into `.env` and is never printed:

```bash
KEY=$(gcloud services api-keys create --project=gcp-fde-project --display-name="ModeraAI API Key" \
  --api-target=service="$MANAGED_SERVICE" --format="value(response.keyString)")
sed -i.bak "s|^API_KEY=.*|API_KEY=$KEY|" .env && rm .env.bak && unset KEY
set -a && source .env && set +a
```

A new key can take a minute or two to start working. When reading the gateway's logs, leave out
`jsonPayload.api_key`: it holds the raw key.

### Checks

```bash
curl -w "  HTTP %{http_code}\n" -X POST "$GATEWAY_URL/moderate" -H "Content-Type: application/json" -d '{"text": "hello"}'
# -> HTTP 401, "Method doesn't allow unregistered callers"

curl -w "  HTTP %{http_code}\n" "$GATEWAY_URL/health"
# -> HTTP 200 (the spec puts no key on /health)

curl -w "  HTTP %{http_code}\n" -X POST "$GATEWAY_URL/moderate?key=$API_KEY" -H "Content-Type: application/json" -d '{"text": "hello"}'
# -> HTTP 200

# the limit registered in the API's service config
CONFIG_ID=$(gcloud api-gateway api-configs describe moderaai-config --api=moderaai-api --project=gcp-fde-project \
  --format="value(serviceConfigId)")
gcloud endpoints configs describe "$CONFIG_ID" --service="$MANAGED_SERVICE" --format="yaml(quota)"
# -> moderate-limit, 1/min/{project}, STANDARD: 10

# 15 requests in a burst through the gateway (load_test.py reads API_KEY from .env)
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
uv run python scripts/load_test.py --url "$GATEWAY_URL" --requests 15
# -> 15/15 succeeded, 0 rejected with 429  (and 40/40 in a second burst)
sleep 90
END=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# how many requests the quota counted (REST call: gcloud has no command for this)
curl -G "https://monitoring.googleapis.com/v3/projects/gcp-fde-project/timeSeries" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  --data-urlencode "filter=metric.type=\"serviceruntime.googleapis.com/quota/rate/net_usage\" AND resource.labels.service=\"$MANAGED_SERVICE\"" \
  --data-urlencode "interval.startTime=$START" --data-urlencode "interval.endTime=$END"
# -> 15 counted in one minute, against a limit of 10
```

### Why it probably did not block

The API's project and the key's project are the same one, `gcp-fde-project`. Quotas are documented as limiting each
*consumer* project, so the likely explanation is that a project's calls to its own API are not held to the limit.
**This is a hypothesis; Google's documentation did not confirm it.** Proving it needs a key from a second project.

---

## Topic 10 — Cost optimization

**Part 1 and 2: the demo script.** It compares Flash and Pro on the same prompt, then sends 6 requests (3 of them
duplicates) to the service and counts the real Gemini calls through `/stats`:

```bash
set -a && source .env && set +a
uv run python scripts/cost_comparison_demo.py
# -> gemini-2.5-flash  input 26, total 919,  ~$0.000092
# -> gemini-2.5-pro    input 26, total 1015, ~$0.002537
# -> Incoming requests: 6 / Real Gemini calls: 3 / Calls avoided by caching: 3
```

The prices in the script are illustrative ($0.0001 and $0.0025 per 1K tokens). Read the ratio (about 25 times), not
the dollars. `/stats` counts per instance and resets on a cold start, so part 2 is only exact when one instance answers
the whole run.

**Part 3: thinking tokens.** Gemini 2.5 "thinks" before it answers, and those tokens are billed as output. The
script's "output tokens" leaves them out. Compare one request with thinking on and off:

```bash
uv run python - <<'EOF'
from google import genai
from google.genai import types
from pydantic import BaseModel

class Verdict(BaseModel):
    flagged: bool
    category: str
    reasoning: str

client = genai.Client(vertexai=True, project="gcp-fde-project", location="us-central1")
text = "This new policy is completely unfair and I'm furious about it."
for budget in (None, 0):
    config = types.GenerateContentConfig(
        system_instruction="You are a content moderation system. Return your verdict.",
        response_mime_type="application/json", response_schema=Verdict,
        thinking_config=None if budget is None else types.ThinkingConfig(thinking_budget=budget))
    r = client.models.generate_content(model="gemini-2.5-flash", contents=text, config=config)
    u = r.usage_metadata
    label = "thinking on (default)" if budget is None else "thinking off (budget 0)"
    print(f"{label:24} answer={u.candidates_token_count} thinking={u.thoughts_token_count or 0} total={u.total_token_count} flagged={r.parsed.flagged}")
EOF
# -> 2026-09-20: thinking on  answer 68, thinking 301, total 414, flagged=False
#               thinking off answer 37, thinking   0, total  82, flagged=False   (about 80% fewer tokens)
# -> 2026-10-11: thinking on  answer 62, thinking  67, total 179, flagged=False
#               thinking off answer 34, thinking   0, total  84, flagged=True    (fewer tokens, different verdict)
```

The numbers change from run to run, and the second run shows why: turning thinking off can change the verdict. Test
it on a batch of real comments before using it. It is **not applied** in `moderaai/main.py`.

The cost levers, biggest first: caching (calls avoided entirely), the model (Flash against Pro), the thinking budget
(tokens per call). `--max-instances` (topic 1) caps the worst case.

---

## Teardown

The service is public (anyone with the URL can cause Gemini calls), so delete everything when you finish.
Before deleting, check each resource holds only this module's things: the image repos hold only `moderaai`
images, one API key matches the name below (the Module 11 Maps key must not be touched), and Firestore holds only
`moderation_cache`.

The gateway first, then its config, then the API (about 2 minutes in total):

```bash
gcloud api-gateway gateways delete moderaai-gateway --location=us-central1 --project=gcp-fde-project --quiet
gcloud api-gateway api-configs delete moderaai-config --api=moderaai-api --project=gcp-fde-project --quiet
gcloud api-gateway apis delete moderaai-api --project=gcp-fde-project --quiet
```

The CI/CD pieces (the repo link before the connection), then the service:

```bash
gcloud builds triggers delete moderaai-deploy-trigger --region=us-central1 --project=gcp-fde-project --quiet
gcloud builds repositories delete cloud-eng-demo --connection=moderaai-github --region=us-central1 --project=gcp-fde-project --quiet
gcloud builds connections delete moderaai-github --region=us-central1 --project=gcp-fde-project --quiet
gcloud run services delete moderaai --region=us-central1 --project=gcp-fde-project --quiet     # all revisions
```

The API key, by its exact resource name, so no other key can be hit by mistake:

```bash
KEYNAME=$(gcloud services api-keys list --project=gcp-fde-project --filter='displayName="ModeraAI API Key"' --format="value(name)")
echo $KEYNAME
gcloud services api-keys delete "$KEYNAME" --project=gcp-fde-project --quiet
```

Data, images and identity:

```bash
gcloud firestore databases delete --database="(default)" --project=gcp-fde-project --quiet
gcloud artifacts repositories delete moderaai-repo --location=us-central1 --project=gcp-fde-project --quiet
gcloud artifacts repositories delete cloud-run-source-deploy --location=us-central1 --project=gcp-fde-project --quiet

for role in roles/aiplatform.user roles/datastore.user; do
  gcloud projects remove-iam-policy-binding gcp-fde-project \
    --member="serviceAccount:moderaai-sa@gcp-fde-project.iam.gserviceaccount.com" --role="$role" --condition=None
done
gcloud iam service-accounts delete moderaai-sa@gcp-fde-project.iam.gserviceaccount.com --project=gcp-fde-project --quiet

# the role given to Cloud Build's own service agent in topic 3
gcloud projects remove-iam-policy-binding gcp-fde-project \
  --member="serviceAccount:service-1039893753206@gcp-sa-cloudbuild.iam.gserviceaccount.com" \
  --role="roles/secretmanager.admin" --condition=None
```

Deleting the GitHub connection leaves GitHub's token behind in Secret Manager. Delete it too:

```bash
gcloud secrets list --project=gcp-fde-project --filter="name~moderaai-github" --format="value(name)"
# -> moderaai-github-github-oauthtoken-<random>
for s in $(gcloud secrets list --project=gcp-fde-project --filter="name~moderaai-github" --format="value(name)"); do
  gcloud secrets delete "$s" --project=gcp-fde-project --quiet
done
```

The Cloud Build GitHub App stays installed on the GitHub account until you remove it at
https://github.com/settings/installations.

The local image, if you built one:

```bash
docker rmi moderaai:local
```

### Verify it is gone

Check every list comes back empty, rather than trusting that `delete` worked:

```bash
gcloud run services list --region=us-central1 --project=gcp-fde-project                # Listed 0 items.
gcloud api-gateway gateways list --location=us-central1 --project=gcp-fde-project      # Listed 0 items.
gcloud api-gateway apis list --project=gcp-fde-project                                 # Listed 0 items.
gcloud builds triggers list --region=us-central1 --project=gcp-fde-project             # Listed 0 items.
gcloud builds connections list --region=us-central1 --project=gcp-fde-project          # Listed 0 items.
gcloud artifacts repositories list --project=gcp-fde-project                           # Listed 0 items.
gcloud firestore databases list --project=gcp-fde-project                              # Listed 0 items.
gcloud secrets list --project=gcp-fde-project                                          # Listed 0 items.
gcloud services api-keys list --project=gcp-fde-project --format="value(displayName)"  # module-11-maps-key only
curl -s -o /dev/null -w "%{http_code}\n" https://moderaai-1039893753206.us-central1.run.app/health   # 404
```

**Left alone on purpose:** the Module 11 Maps key, the enabled APIs, the retained Cloud Logging entries, and the shared
Cloud Build source bucket `gcp-fde-project_cloudbuild` (used by earlier modules too; its archives contain this repo's
files, never `.env` or tokens).

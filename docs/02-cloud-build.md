# 2. Cloud Build

## What Is It?

Up to now, when you deployed a service, your own laptop did the work of building the Docker container before shipping it off. Cloud Build is a factory in the cloud that does that building step for you — it takes your source code, builds the container image, and stores it, all on Google's machines, not yours.

## Why It Matters for AI Engineers

Once a team is bigger than one person, "build it on my laptop" stops being reliable — different machines, different installed versions, someone's laptop is asleep. Cloud Build gives everyone the exact same, repeatable build environment, and it's also the engine that makes CI/CD (the next topic) possible — you can't auto-deploy on every push if there's no automatic way to build first.

## Key Concepts

| Term | Definition |
|---|---|
| Build | The process of turning your Dockerfile + source into a runnable container image |
| `cloudbuild.yaml` | A file describing the build steps, in order |
| Build log | Streamed, timestamped output of everything the build did |
| Artifact Registry | Where the finished image gets stored after the build (from Module 14) |

## How It Fits Together

```text
Source code ──► Cloud Build ──► docker build (Dockerfile) ──► push to Artifact Registry ──► deploy to Cloud Run
```

## Hands-On

**Console:** Cloud Build → **History** — after running a build, click into it to see the same log live.

**CLI** (run from the **repo root**; full steps in [`commands.md`](../commands.md), topic 2):

```bash
# Manual, one-off remote build: no local Docker needed.
# Submitted from the repo root, because that is what topic 3's trigger checks out too.
gcloud builds submit --project=gcp-fde-project \
  --config=moderaai/cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_TAG=v1.0.0 .
```

### The Dockerfile, and uv

The Dockerfile is the recipe for the image. In short, it:

1. starts from a small official Python 3.12 image,
2. installs the packages from `requirements.txt` with **uv**,
3. copies in `main.py`,
4. switches to a normal user, so the app doesn't run as root,
5. starts the app with `gunicorn`, a production web server.

**uv** is a tool that installs Python packages, like `pip`, but many times faster. In the Dockerfile it's one copied
file and one install line:

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:0.8.14 /uv /bin/uv
RUN uv pip install --system --no-cache -r requirements.txt
```

The version is pinned (`0.8.14`), so every build uses the same uv. `--system` installs into the image's own Python,
because a container doesn't need a virtual environment. You can use uv on your laptop too: see the setup in `commands.md`.

`cloudbuild.yaml` (in `moderaai/`):

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    dir: 'moderaai'
    args: ['build', '-t', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/moderaai-repo/moderaai:${_TAG}', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/moderaai-repo/moderaai:${_TAG}']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - run
      - deploy
      - moderaai
      - '--image=${_REGION}-docker.pkg.dev/${PROJECT_ID}/moderaai-repo/moderaai:${_TAG}'
      - '--region=${_REGION}'
      - '--allow-unauthenticated'
      - '--service-account=moderaai-sa@${PROJECT_ID}.iam.gserviceaccount.com'
      - '--set-env-vars=PROJECT_ID=${PROJECT_ID},LOCATION=${_REGION},MODERATION_POLICY=standard,...'
      - '--max-instances=10'
      - '--timeout=30'
substitutions:
  _REGION: us-central1
  _TAG: latest
images:
  - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/moderaai-repo/moderaai:${_TAG}'
options:
  logging: CLOUD_LOGGING_ONLY
```

The deploy step names the service account and every setting. Without them, a deploy keeps whatever the service had
last, which can be the wrong policy after a rollback (topic 5). The `logging` option is needed by topic 3's trigger.

The `dir:` on the build step matters more than it looks — without it, the docker build step would use whatever the *build's source root* happens to be as its context. That's harmless when you happen to submit from inside `moderaai/` itself, but it silently breaks the moment the same file is triggered by a real GitHub push (topic 3), which always checks out the *entire* repo. Pointing `dir:` at this module's exact folder makes the config work identically either way — which is also why the manual command above submits from the repo root instead of `moderaai/`: so the "manual" and "automatic" paths are tested against the literal same conditions.

## How We Test It

Run the `gcloud builds submit` command above and watch the log stream in the terminal in real time — three visibly distinct steps scroll past (docker build, docker push, gcloud run deploy). Then open Cloud Build → History in the Console and click into that same build to show students it's a permanent, auditable record, not just terminal output that vanishes.

## Common Pitfalls

- Forgetting `--region` matches your Artifact Registry repo's region — build succeeds, push fails
- Editing `cloudbuild.yaml` and forgetting substitution variables (`${_REGION}`) need a matching `substitutions:` block or a `--substitutions` flag
- Confusing "build" (make the image) with "deploy" (run the image) — Cloud Build can do both if you tell it to, like the config above does

## Quick Recap

1. What does Cloud Build produce, and where does it store it?
2. Why is a shared, remote build environment more reliable than "build on my laptop"?
3. What are the three steps in this module's `cloudbuild.yaml`?

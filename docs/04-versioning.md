# 4. Versioning

## What Is It?

If you label every batch of cookies "cookies," you can never tell a fresh batch from a stale one. Versioning is putting a clear label — `v1.0.0`, `v2.0.0` — on every build of ModeraAI, both on the container image and on the Cloud Run revision it creates, so at any moment you can say exactly what code is answering requests.

## Why It Matters for AI Engineers

AI services are especially easy to accidentally "silently change" — a tweaked prompt, a swapped model name, a different moderation policy — none of which look like a code change at a glance. Without versioning, "it used to work" is undebuggable, because you can't prove what was actually running when it worked. Versioning is also what makes rollbacks (next topic) possible at all — you can't roll back to something you never labeled.

## Key Concepts

| Term | Definition |
|---|---|
| Image tag | The version label on the container image itself (`moderaai:v2.0.0`) |
| Cloud Run revision | An immutable, addressable snapshot Cloud Run creates every time you deploy |
| Traffic split | What percentage of live traffic each revision currently receives |
| Semantic versioning | `MAJOR.MINOR.PATCH` — a convention for what a version bump means |

## How It Fits Together

```text
moderaai:v1.0.0  (MODERATION_POLICY=standard) ──► revision 1 ──► 100% of traffic ─────────┐
                                                                                          ├──► the live service
moderaai:v2.0.0  (MODERATION_POLICY=strict)   ──► revision 2 ──► 0% until promoted ┄┄┄┄┄┄┄┘
                                                                  (reachable on its own tagged URL)
```

## Hands-On

```bash
# Build and tag the v2 image
gcloud builds submit moderaai --project=gcp-fde-project \
  --tag=us-central1-docker.pkg.dev/gcp-fde-project/moderaai-repo/moderaai:v2.0.0

# Deploy v2 as a new revision with the strict policy, at 0% traffic, with its own address (tag v2-0-0)
gcloud run deploy moderaai --project=gcp-fde-project --region=us-central1 \
  --image=us-central1-docker.pkg.dev/gcp-fde-project/moderaai-repo/moderaai:v2.0.0 \
  --service-account=moderaai-sa@gcp-fde-project.iam.gserviceaccount.com \
  --set-env-vars=PROJECT_ID=gcp-fde-project,LOCATION=us-central1,MODERATION_POLICY=strict,MODEL_NAME=gemini-2.5-flash,GEMINI_TIMEOUT_MS=10000,CACHE_TTL_SECONDS=3600 \
  --no-traffic --tag=v2-0-0 --quiet

# List every revision that exists
gcloud run revisions list --service=moderaai --region=us-central1 --project=gcp-fde-project
```

`--set-env-vars` replaces **all** the settings, so every one is listed, not just the policy. "v2" is the same code
as v1; only the policy setting differs.

## How We Test It

`gcloud run revisions list` shows both revisions side by side, neither replacing the other. Then send the same comment to each version: v1 through the main address, v2 through its own tagged address (`https://v2-0-0---moderaai-mewtpyvzkq-uc.a.run.app`). "I disagree with this policy." comes back `flagged: false` from v1 and `flagged: true` from v2.

## Common Pitfalls

- Deploying without `--no-traffic` and accidentally sending 100% of live traffic straight to an untested v2
- Reusing the `:latest` tag for a real change — it silently overwrites the previous meaning of "latest" with no record of what changed
- Assuming a new Cloud Run revision replaces the old one — it doesn't; both exist until you explicitly delete one
- Using a tag shorter than 3 characters: `--tag=v2` is refused, `v2-0-0` works

## Quick Recap

1. What's the difference between an image tag and a Cloud Run revision?
2. Why does `--no-traffic` matter when deploying a new version?
3. Why is `:latest` a bad tag to rely on for anything you'd need to roll back to?

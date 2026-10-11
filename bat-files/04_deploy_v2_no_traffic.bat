@echo off
REM Topic 4 - Versioning. Builds and tags v2 explicitly (stricter moderation
REM policy via env var), deploys it as a new revision, but keeps it at 0%%
REM traffic so v1 stays live - this is what topic 5's rollback demo undoes.
REM Requires: 00_setup_vars.bat already run, v1 already deployed (topic 1).

echo == building and tagging v2.0.0 ==
gcloud builds submit --tag %REGION%-docker.pkg.dev/%PROJECT_ID%/%ARTIFACT_REPO%/moderaai:v2.0.0 moderaai

echo == deploying v2 with the strict policy, at 0%% traffic ==
gcloud run deploy %SERVICE_NAME% ^
  --image=%REGION%-docker.pkg.dev/%PROJECT_ID%/%ARTIFACT_REPO%/moderaai:v2.0.0 ^
  --region=%REGION% ^
  --service-account=moderaai-sa@%PROJECT_ID%.iam.gserviceaccount.com ^
  --set-env-vars=PROJECT_ID=%PROJECT_ID%,LOCATION=%LOCATION%,MODERATION_POLICY=strict,MODEL_NAME=%MODEL_NAME%,GEMINI_TIMEOUT_MS=%GEMINI_TIMEOUT_MS%,CACHE_TTL_SECONDS=%CACHE_TTL_SECONDS% ^
  --no-traffic ^
  --tag=v2

echo.
echo == every revision that now exists ==
gcloud run revisions list --service=%SERVICE_NAME% --region=%REGION%

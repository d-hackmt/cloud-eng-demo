@echo off
REM Topic 1 - Scaling. Deploys ModeraAI v1 with a generous instance ceiling,
REM then load-tests it. Run again after redeploying with --max-instances=2
REM to show the ceiling effect.
REM Requires: 00_setup_vars.bat and 00a_initial_setup.bat already run.

echo == deploying ModeraAI v1 (max-instances=10) ==
gcloud run deploy %SERVICE_NAME% --source moderaai ^
  --region=%REGION% ^
  --allow-unauthenticated ^
  --service-account=moderaai-sa@%PROJECT_ID%.iam.gserviceaccount.com ^
  --set-env-vars=PROJECT_ID=%PROJECT_ID%,LOCATION=%LOCATION%,MODERATION_POLICY=%MODERATION_POLICY%,MODEL_NAME=%MODEL_NAME%,GEMINI_TIMEOUT_MS=%GEMINI_TIMEOUT_MS%,CACHE_TTL_SECONDS=%CACHE_TTL_SECONDS% ^
  --max-instances=10 ^
  --timeout=30

echo.
echo == IMPORTANT: copy the Service URL printed above into 00_setup_vars.bat as SERVICE_URL, then re-run 00_setup_vars.bat ==
echo.

echo == running the load test (50 concurrent requests) ==
python load_test.py --url %SERVICE_URL% --requests 50

echo.
echo To see the ceiling effect: redeploy with --max-instances=2 and run load_test.py again.

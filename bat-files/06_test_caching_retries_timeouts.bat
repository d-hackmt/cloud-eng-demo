@echo off
REM Topics 6, 7, 8 - Caching, Retry Strategies, Timeouts.
REM All three are built into moderaai/main.py itself; this script just fires
REM the curl calls that demo each one. Requires: 00_setup_vars.bat run,
REM v1 deployed and SERVICE_URL filled in.

echo ============================================
echo Topic 6 - Caching: same text, called twice
echo ============================================
echo -- call 1 (expect cache_hit: false) --
curl -w "\nTime: %%{time_total}s\n" -X POST %SERVICE_URL%/moderate -H "Content-Type: application/json" -d "{\"text\": \"Great article, thanks for sharing!\"}"
echo.
echo -- call 2, identical text (expect cache_hit: true, much faster) --
curl -w "\nTime: %%{time_total}s\n" -X POST %SERVICE_URL%/moderate -H "Content-Type: application/json" -d "{\"text\": \"Great article, thanks for sharing!\"}"

echo.
echo ============================================
echo Topic 7 - Retry Strategies: forces 2 failures then succeeds
echo ============================================
curl -X POST "%SERVICE_URL%/moderate?simulate_transient_failure=true" -H "Content-Type: application/json" -d "{\"text\": \"retry demo text\"}"
echo (check Cloud Run logs for the 3 attempts: gcloud run services logs read %SERVICE_NAME% --region=%REGION%)

echo.
echo ============================================
echo Topic 8 - Timeouts: deliberately stalls past the timeout
echo ============================================
curl -w "\nTime: %%{time_total}s\n" -X POST "%SERVICE_URL%/moderate?simulate_hang=true" -H "Content-Type: application/json" -d "{\"text\": \"timeout demo text\"}"

@echo off
REM Topic 5 - Rollbacks. Promotes v2 to 100%% traffic, proves it over-flags
REM safe text, then rolls traffic back to v1 and proves the fix - all via
REM traffic changes, no rebuild.
REM Requires: 04_deploy_v2_no_traffic.bat already run.

echo == step 1: promote v2 to 100%% traffic (simulating "we shipped it") ==
gcloud run services update-traffic %SERVICE_NAME% --region=%REGION% --to-latest

echo.
echo == step 2: call /moderate with a mild, clearly-safe comment ==
echo (expect: incorrectly flagged=true under v2's strict policy)
curl -X POST %SERVICE_URL%/moderate -H "Content-Type: application/json" -d "{\"text\": \"I disagree with this policy.\"}"

echo.
echo == step 3: find v1's revision name and roll traffic back to it ==
gcloud run revisions list --service=%SERVICE_NAME% --region=%REGION%
echo (copy the v1 revision name, e.g. moderaai-00001-abc, then run:)
echo   gcloud run services update-traffic %SERVICE_NAME% --region=%REGION% --to-revisions=REVISION_NAME=100

echo.
echo == step 4: after rollback, call the same text again ==
echo (expect: correctly flagged=false now that v1/standard is live again)
curl -X POST %SERVICE_URL%/moderate -H "Content-Type: application/json" -d "{\"text\": \"I disagree with this policy.\"}"

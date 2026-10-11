@echo off
REM Shared variables for every .bat script in this module.
REM Run this FIRST, in the SAME Command Prompt window you'll run the rest in.

set PROJECT_ID=agentic-ai-capstone-1
set REGION=us-central1
set LOCATION=us-central1

set SERVICE_NAME=moderaai
set ARTIFACT_REPO=moderaai-repo

REM "standard" for v1, "strict" for v2 (used in the topic 5 rollback demo)
set MODERATION_POLICY=standard

REM Verify this is still a current, non-deprecated GA model ID at build time.
set MODEL_NAME=gemini-2.5-flash
set GEMINI_TIMEOUT_MS=10000
set CACHE_TTL_SECONDS=3600

REM DUMMY VALUE - replace with your GitHub username (topic 3, CI/CD trigger)
set GITHUB_USERNAME=your-github-username

REM Filled in AFTER 01_deploy_and_load_test.bat prints the Cloud Run URL
set SERVICE_URL=https://REPLACE-ME-AFTER-DEPLOY.run.app

set API_ID=moderaai-api
set API_CONFIG_ID=moderaai-config
set GATEWAY_ID=moderaai-gateway

REM Filled in AFTER topic 9's API Gateway deploy
set GATEWAY_URL=https://REPLACE-ME-AFTER-GATEWAY-DEPLOY.gateway.dev
set API_KEY=REPLACE-ME-AFTER-API-KEY-CREATE

echo Loaded vars: PROJECT_ID=%PROJECT_ID%, REGION=%REGION%, SERVICE_NAME=%SERVICE_NAME%

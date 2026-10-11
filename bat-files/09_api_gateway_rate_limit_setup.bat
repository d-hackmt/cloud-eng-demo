@echo off
REM Topic 9 - Rate Limiting via API Gateway's built-in quota.
REM Requires: v1 deployed (topic 1), and 09_openapi_spec.yaml edited to have
REM the real ModeraAI Cloud Run URL in place of MODERAAI_SERVICE_URL_HERE.

echo == creating the logical API ==
gcloud api-gateway apis create %API_ID%

echo == creating an API config from the OpenAPI spec (this is where the quota is declared) ==
gcloud api-gateway api-configs create %API_CONFIG_ID% ^
  --api=%API_ID% ^
  --openapi-spec=09_openapi_spec.yaml ^
  --backend-auth-service-account=moderaai-sa@%PROJECT_ID%.iam.gserviceaccount.com

echo == deploying the gateway ==
gcloud api-gateway gateways create %GATEWAY_ID% ^
  --api=%API_ID% ^
  --api-config=%API_CONFIG_ID% ^
  --location=%REGION%

echo.
echo == getting the gateway hostname ==
gcloud api-gateway gateways describe %GATEWAY_ID% --location=%REGION% --format="value(defaultHostname)"

echo.
echo IMPORTANT: copy the printed hostname into 00_setup_vars.bat as GATEWAY_URL
echo (as https://HOSTNAME), then re-run 00_setup_vars.bat.
echo.

echo == creating an API key ==
echo (the quota is scoped "per project" and API Gateway identifies the calling
echo  project via this key - without one, quota tracking has nothing to key off)
gcloud services api-keys create --display-name="ModeraAI API Key"
echo Copy the "keyString" from the output above (or run:
echo   gcloud services api-keys list
echo   gcloud services api-keys get-key-string KEY_ID
echo to retrieve it). Save it into 00_setup_vars.bat as API_KEY.

echo.
echo Test the quota: python load_test.py --url %%GATEWAY_URL%% --requests 15 --api-key %%API_KEY%%
echo Expect the first 10 to succeed and the rest to come back as 429.

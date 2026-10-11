@echo off
REM Tears down everything this module created.
REM Requires: 00_setup_vars.bat already run in this same window.

echo == deleting the API Gateway, config, and API (topic 9) ==
gcloud api-gateway gateways delete %GATEWAY_ID% --location=%REGION% --quiet
gcloud api-gateway api-configs delete %API_CONFIG_ID% --api=%API_ID% --quiet
gcloud api-gateway apis delete %API_ID% --quiet

echo == deleting the CI/CD trigger (topic 3) ==
gcloud builds triggers delete moderaai-deploy-trigger --quiet

echo == deleting the Cloud Run service (all revisions, v1 and v2) ==
gcloud run services delete %SERVICE_NAME% --region=%REGION% --quiet

echo == deleting the Artifact Registry repo (all images) ==
gcloud artifacts repositories delete %ARTIFACT_REPO% --location=%REGION% --quiet

echo == deleting the Firestore cache documents ==
echo (Firestore Native database itself is project-wide and shared - not deleted here;
echo  delete individual docs via Console if you want a clean cache: Firestore -^> moderation_cache)

echo == deleting the service account ==
gcloud iam service-accounts delete moderaai-sa@%PROJECT_ID%.iam.gserviceaccount.com --quiet

echo.
echo All done.

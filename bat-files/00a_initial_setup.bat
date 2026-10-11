@echo off
REM One-time setup: enable APIs, create the Artifact Registry repo, a runtime
REM service account with Firestore + Vertex AI access, and a Firestore database
REM (used for topic 6's caching).
REM Requires: 00_setup_vars.bat already run in this same window.

echo == enabling required APIs ==
gcloud services enable run.googleapis.com cloudbuild.googleapis.com ^
  artifactregistry.googleapis.com firestore.googleapis.com ^
  aiplatform.googleapis.com apigateway.googleapis.com ^
  servicemanagement.googleapis.com servicecontrol.googleapis.com

echo == creating the Artifact Registry repo ==
gcloud artifacts repositories create %ARTIFACT_REPO% ^
  --repository-format=docker ^
  --location=%REGION% ^
  --description="Container images for ModeraAI (Module 17)"

echo == creating the Firestore database (Native mode), if it doesn't exist ==
gcloud firestore databases create --location=%LOCATION% --type=firestore-native

echo == creating the service's runtime service account ==
gcloud iam service-accounts create moderaai-sa ^
  --display-name="ModeraAI Runtime SA"

echo == granting least-privilege roles it needs at runtime ==
gcloud projects add-iam-policy-binding %PROJECT_ID% ^
  --member="serviceAccount:moderaai-sa@%PROJECT_ID%.iam.gserviceaccount.com" ^
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding %PROJECT_ID% ^
  --member="serviceAccount:moderaai-sa@%PROJECT_ID%.iam.gserviceaccount.com" ^
  --role="roles/datastore.user"

echo.
echo Setup complete. Next: 01_deploy_and_load_test.bat

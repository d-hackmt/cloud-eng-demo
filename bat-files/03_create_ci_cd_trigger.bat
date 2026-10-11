@echo off
REM Topic 3 - CI/CD. Recreates, by command, the same trigger set up via the
REM Console's "Connect Repository" flow (Cloud Build -> Triggers).
REM
REM IMPORTANT: the GitHub connection itself is a one-time, Console-based,
REM OAuth-style step that cannot be scripted - do that FIRST:
REM   Cloud Build -> Triggers -> Connect Repository -> GitHub -> authorize
REM   the Google Cloud Build GitHub App -> select this repo.
REM Only after that connection exists will this command succeed.
REM Requires: 00_setup_vars.bat already run.

gcloud builds triggers create github ^
  --repo-name=GCP-UDMEY ^
  --repo-owner=%GITHUB_USERNAME% ^
  --branch-pattern="^main$" ^
  --build-config=code/17-production-ai-engineering/moderaai/cloudbuild.yaml ^
  --name=moderaai-deploy-trigger

echo.
echo Trigger created. Test it: make a small change under code/17-production-ai-engineering/moderaai/,
echo git commit, git push, then watch Cloud Build -^> History.

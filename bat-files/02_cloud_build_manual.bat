@echo off
REM Topic 2 - Cloud Build. A manual, one-off remote build using cloudbuild.yaml
REM (build -> push -> deploy), run directly from the terminal so students see
REM the log stream live.
REM Requires: 00_setup_vars.bat and 00a_initial_setup.bat already run.
REM Run from code/17-production-ai-engineering, same as every other script here.
REM
REM IMPORTANT: this submits the WHOLE repo as build source (pushd's up to the
REM repo root first) rather than just the moderaai/ subfolder - that's not
REM an accident. cloudbuild.yaml's build step uses `dir:` to find moderaai/
REM from a repo-root workspace, because that's what topic 3's CI/CD trigger
REM always gives it too (a trigger checks out the whole connected repo, never
REM just this module's subfolder). Submitting from the repo root here keeps
REM this manual run and the automated trigger using the identical config,
REM unmodified, exactly as a real team would want.

pushd ..\..
gcloud builds submit --config=code/17-production-ai-engineering/moderaai/cloudbuild.yaml --substitutions=_REGION=%REGION%,_TAG=v1.0.0 .
popd

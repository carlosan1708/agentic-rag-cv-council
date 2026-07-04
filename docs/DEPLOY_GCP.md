# Deploying to Google Cloud (Cloud Run + Cloud Storage)

The app stays a plain Streamlit app. It runs as a container on **Cloud Run** and persists
analysis history as JSON objects in a **Google Cloud Storage** bucket (Cloud Run's local
filesystem is ephemeral, so the SQLite backend used locally would lose data on every restart).

```
Browser ──HTTPS──▶ Cloud Run (Streamlit container)
                        │
                        ├── Gemini / OpenAI / Anthropic APIs  (analysis)
                        ├── GCS bucket  gs://<project>-cv-advisor-history  (history JSON)
                        └── Secret Manager  (GOOGLE_API_KEY)
```

## How storage selection works

| Env var | Effect |
|---|---|
| `GCS_BUCKET` | When set, history is stored in that bucket under `history/{owner}/{id}.json`. When unset, the local SQLite backend (`DATA_DIR/history.db`) is used. |
| `HISTORY_SCOPE` | `session` (recommended for hosted deployments): each browser session gets a random owner id, so visitors never see each other's history. `shared` (default, for local use): one shared "local" owner that persists across restarts. |
| `ONLINE_MODE` | `true` enables the hosted-demo flow (pre-configured system key, cheap model locked). |

Credentials: the GCS client uses Application Default Credentials — automatic on Cloud Run via the
service account; locally run `gcloud auth application-default login` if you want to test the GCS
backend from your machine.

## One-command deploy

```bash
gcloud auth login
export GOOGLE_API_KEY=your-gemini-key   # only needed the first time (creates the secret)
./scripts/deploy_gcp.sh YOUR_PROJECT_ID [REGION] [BUCKET_NAME]
```

The script:
1. Enables the Cloud Run, Cloud Build, Storage, Secret Manager and Artifact Registry APIs.
2. Creates the history bucket (uniform bucket-level access) if it doesn't exist.
3. Grants the Cloud Run service account `roles/storage.objectAdmin` on that bucket only.
4. Creates the `GOOGLE_API_KEY` secret (from `$GOOGLE_API_KEY`) and grants the service account access.
5. Builds the container from the repo's `Dockerfile` via Cloud Build and deploys it with
   `ONLINE_MODE=true`, `GCS_BUCKET=...` and `HISTORY_SCOPE=session`.

## Manual steps (what the script does, spelled out)

```bash
PROJECT_ID=your-project
REGION=europe-west1
BUCKET=${PROJECT_ID}-cv-advisor-history

gcloud config set project $PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
    storage.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com

# Bucket for history
gcloud storage buckets create gs://$BUCKET --location=$REGION --uniform-bucket-level-access

# Least-privilege access for the runtime service account
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
RUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
    --member=serviceAccount:$RUN_SA --role=roles/storage.objectAdmin

# API key as a secret (never an env var in the console)
printf 'your-gemini-key' | gcloud secrets create GOOGLE_API_KEY --data-file=-
gcloud secrets add-iam-policy-binding GOOGLE_API_KEY \
    --member=serviceAccount:$RUN_SA --role=roles/secretmanager.secretAccessor

# Build + deploy from source
gcloud run deploy ai-cv-advisory-board \
    --source . --region $REGION --allow-unauthenticated \
    --memory 1Gi --timeout 600 --max-instances 3 \
    --set-env-vars "ONLINE_MODE=true,GCS_BUCKET=$BUCKET,HISTORY_SCOPE=session" \
    --set-secrets "GOOGLE_API_KEY=GOOGLE_API_KEY:latest"
```

## Updating the app

Re-run the deploy (it rebuilds from source):

```bash
gcloud run deploy ai-cv-advisory-board --source . --region $REGION
```

Env vars and secrets are preserved between deploys unless you override them.

## Costs & scaling notes

- Cloud Run scales to zero — you pay nothing while idle. `--max-instances 3` caps runaway costs.
- Analyses are long-running (up to ~2 min); `--timeout 600` covers Streamlit's long websocket
  requests. Keep CPU allocated during requests (the default) so CrewAI isn't throttled mid-run.
- The bucket stores small JSON documents; storage cost is negligible. Add a lifecycle rule if you
  want automatic cleanup, e.g. delete history objects after 90 days:

  ```bash
  cat > /tmp/lifecycle.json <<'JSON'
  {"rule": [{"action": {"type": "Delete"}, "condition": {"age": 90}}]}
  JSON
  gcloud storage buckets update gs://$BUCKET --lifecycle-file=/tmp/lifecycle.json
  ```

## Privacy

- `HISTORY_SCOPE=session` means a visitor only ever sees analyses created in their own browser
  session; the "Delete all my data" button removes their objects from the bucket.
- CVs themselves are never persisted — only the generated reports and the job-description snippet.
- To disable persistence entirely on the hosted app, deploy without `GCS_BUCKET`; history then
  writes to the ephemeral container disk and disappears on restart.

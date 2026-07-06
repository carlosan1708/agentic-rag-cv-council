#!/usr/bin/env bash
# Deploys the app to Google Cloud Run with a GCS bucket for analysis history.
#
# Usage:
#   ./scripts/deploy_gcp.sh PROJECT_ID [REGION] [BUCKET_NAME]
#
# Prerequisites:
#   - gcloud CLI authenticated (gcloud auth login)
#   - Billing enabled on the project
#   - A GOOGLE_API_KEY secret (created automatically if GOOGLE_API_KEY is exported)
set -euo pipefail

PROJECT_ID=${1:?Usage: deploy_gcp.sh PROJECT_ID [REGION] [BUCKET_NAME]}
REGION=${2:-europe-west1}
BUCKET=${3:-${PROJECT_ID}-cv-advisor-history}
SERVICE=ai-cv-advisory-board

gcloud config set project "$PROJECT_ID"

echo "==> Enabling required APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
    storage.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com

echo "==> Creating history bucket gs://$BUCKET (if missing)..."
gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1 \
    || gcloud storage buckets create "gs://$BUCKET" --location="$REGION" --uniform-bucket-level-access

echo "==> Granting the Cloud Run service account access to the bucket..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
RUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
    --member="serviceAccount:${RUN_SA}" --role=roles/storage.objectAdmin >/dev/null

echo "==> Ensuring the GOOGLE_API_KEY secret exists..."
if ! gcloud secrets describe GOOGLE_API_KEY >/dev/null 2>&1; then
    if [[ -n "${GOOGLE_API_KEY:-}" ]]; then
        printf '%s' "$GOOGLE_API_KEY" | gcloud secrets create GOOGLE_API_KEY --data-file=-
    else
        echo "ERROR: Secret GOOGLE_API_KEY not found."
        echo "Create it with:  printf 'your-gemini-key' | gcloud secrets create GOOGLE_API_KEY --data-file=-"
        exit 1
    fi
fi
gcloud secrets add-iam-policy-binding GOOGLE_API_KEY \
    --member="serviceAccount:${RUN_SA}" --role=roles/secretmanager.secretAccessor >/dev/null

echo "==> Deploying to Cloud Run..."
gcloud run deploy "$SERVICE" \
    --source . \
    --region "$REGION" \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --timeout 600 \
    --max-instances 3 \
    --set-env-vars "ONLINE_MODE=true,GCS_BUCKET=${BUCKET},HISTORY_SCOPE=session" \
    --set-secrets "GOOGLE_API_KEY=GOOGLE_API_KEY:latest"

echo "==> Done. Service URL:"
gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)'

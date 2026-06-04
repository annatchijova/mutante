#!/usr/bin/env bash
# Copyright 2026 Anna Tchijova, Gemini
set -eo pipefail
PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="mutante-core-engine"
REGION="us-central1"

echo "[+] Construyendo imagen..."
gcloud builds submit --tag "gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest" .

echo "[+] Desplegando en Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest" \
    --region "${REGION}" \
    --allow-unauthenticated \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},BIGQUERY_DATASET=mutante_analytics,BIGQUERY_TABLE=mutante_audits" \
    --set-secrets "ELASTIC_CLOUD_ID=ELASTIC_CLOUD_ID:latest,ELASTIC_API_KEY=ELASTIC_API_KEY:latest"

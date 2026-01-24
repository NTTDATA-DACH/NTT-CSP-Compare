#!/bin/bash
set -e
set -o pipefail

ENV_FILE="$(dirname "$0")/.env"

# Helper to manage environment variables
get_or_ask_var() {
    local var_name=$1
    local prompt_msg=$2
    if [ -z "${!var_name-}" ]; then
        if [ -f "$ENV_FILE" ]; then
            val=$(grep "^${var_name}=" "$ENV_FILE" | cut -d'=' -f2-)
            if [ -n "$val" ]; then export "$var_name"="$val"; return; fi
        fi
        read -p "$prompt_msg: " user_input
        echo "${var_name}=${user_input}" >> "$ENV_FILE"
        export "$var_name"="$user_input"
    fi
}

# 1. Load basic project info
get_or_ask_var "GCP_PROJECT_ID" "Enter your GCP Project ID"
get_or_ask_var "ARTIFACT_REGISTRY_REPO" "Enter Artifact Registry Repo Name"
get_or_ask_var "IMAGE_NAME" "Enter Container Image Name"
get_or_ask_var "SERVICE_ACCOUNT_EMAIL" "Enter Service Account Email"

# 2. Fetch infra data from Terraform
fetch_infra() {
    echo "Querying Terraform for infrastructure details..."
    pushd terraform > /dev/null
    GCP_REGION=$(terraform output -raw region 2>/dev/null || echo "us-central1")
    GCS_BUCKET_NAME=$(terraform output -raw bucket_name 2>/dev/null || echo "")
    popd > /dev/null

    if [ -z "$GCS_BUCKET_NAME" ]; then
        echo "Error: Could not find 'bucket_name' output. Run 'terraform apply' first."
        exit 1
    fi
}

# 3. Ensure Artifact Registry exists
ensure_repo() {
    if ! gcloud artifacts repositories describe "$ARTIFACT_REGISTRY_REPO" --location="$GCP_REGION" &>/dev/null; then
        echo "Creating Artifact Registry repository..."
        gcloud artifacts repositories create "$ARTIFACT_REGISTRY_REPO" \
            --repository-format=docker --location="$GCP_REGION"
    fi
}

build() {
    fetch_infra
    ensure_repo
    local image_uri="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REGISTRY_REPO}/${IMAGE_NAME}:latest"
    echo "Building and pushing container: ${image_uri}"
    gcloud builds submit --tag "${image_uri}" .
}

deploy() {
    build
    local image_uri="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REGISTRY_REPO}/${IMAGE_NAME}:latest"
    
    echo "Deploying Cloud Run Job: csp-comparator-job..."
    gcloud run jobs deploy "csp-comparator-job" \
        --image "$image_uri" \
        --region "$GCP_REGION" \
        --service-account "$SERVICE_ACCOUNT_EMAIL" \
        --set-env-vars "GCP_PROJECT_ID=${GCP_PROJECT_ID},BUCKET_NAME=${GCS_BUCKET_NAME},AI_LOCATION=${GCP_REGION}" \
        --cpu 2 --memory 4Gi \
        --max-retries 3
}

trigger() {
    fetch_infra
    echo "Executing job..."
    gcloud run jobs execute "csp-comparator-job" --region "$GCP_REGION" --args="$*"
}

case "$1" in
    build) build ;;
    deploy) deploy ;;
    trigger) shift; trigger "$@" ;;
    *) echo "Usage: $0 {build|deploy|trigger}"; exit 1 ;;
esac
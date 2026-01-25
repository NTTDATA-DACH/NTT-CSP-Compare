#!/bin/bash

# NOTE: To ensure variables stay in your terminal, run this script as:
# source manage.sh [command]

# No 'set -e' at the very top because sourcing a failing script 
# would close your entire Cloud Shell session. We use it inside functions instead.

check_and_export() {
    local var_name=$1
    local prompt_msg=$2
    
    if [ -z "${!var_name-}" ]; then
        echo -n "$prompt_msg: "
        read -r user_input
        if [ -z "$user_input" ]; then
            echo "Error: $var_name is required."
            return 1
        fi
        # This exports to the parent shell if the script is sourced
        export "$var_name"="$user_input"
    fi
}

# 1. Ensure project variables are in the ENV
check_and_export "GCP_PROJECT_ID" "Enter GCP Project ID"
check_and_export "ARTIFACT_REGISTRY_REPO" "Enter Artifact Registry Repo Name"
check_and_export "IMAGE_NAME" "Enter Container Image Name"
check_and_export "SERVICE_ACCOUNT_EMAIL" "Enter Service Account Email"

# 2. Pull from Terraform into ENV
fetch_infra() {
    if [ ! -d "terraform" ]; then
        echo "Error: No 'terraform' directory found."
        return 1
    fi
    
    echo "--- Pulling Infra data into ENV ---"
    # We export these so they are available globally in your session
    export GCP_REGION=$(terraform -chdir=terraform output -raw region 2>/dev/null || echo "us-central1")
    export GCS_BUCKET_NAME=$(terraform -chdir=terraform output -raw bucket_name 2>/dev/null || echo "")
}

deploy() {
    (
        set -e
        fetch_infra
        local image_uri="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REGISTRY_REPO}/${IMAGE_NAME}:latest"
        
        echo "--- Building ---"
        gcloud builds submit --tag "$image_uri" --project "$GCP_PROJECT_ID" .
        
        echo "--- Deploying Job ---"
        gcloud run jobs deploy "csp-comparator-job" \
            --image "$image_uri" \
            --region "$GCP_REGION" \
            --project "$GCP_PROJECT_ID" \
            --service-account "$SERVICE_ACCOUNT_EMAIL" \
            --set-env-vars "GCP_PROJECT_ID=${GCP_PROJECT_ID},BUCKET_NAME=${GCS_BUCKET_NAME},AI_LOCATION=${GCP_REGION}" \
            --cpu 2 --memory 4Gi
    )
}

trigger() {
    fetch_infra
    gcloud run jobs execute "csp-comparator-job" \
        --region "$GCP_REGION" \
        --project "$GCP_PROJECT_ID" \
        --args="$*"
}

# Handle commands
case "${1-}" in
    deploy)  deploy ;;
    trigger) shift; trigger "$@" ;;
    build)   fetch_infra; gcloud builds submit --tag "${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REGISTRY_REPO}/${IMAGE_NAME}:latest" --project "$GCP_PROJECT_ID" . ;;
    *) echo "Usage: source manage.sh {deploy|trigger|build}" ;;
esac
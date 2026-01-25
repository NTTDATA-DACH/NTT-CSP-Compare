#!/bin/bash

# NOTE: To ensure variables stay in your terminal, run this script as:
# source manage.sh [command]

# This script now acts as a wrapper for Terraform and gcloud commands,
# sourcing all its configuration from the Terraform state.

# 1. Fetch all required infrastructure details from Terraform
fetch_infra() {
    echo "Querying Terraform for infrastructure details..."
    pushd terraform > /dev/null

    # Run terraform output once and capture the JSON output
    TF_OUTPUT=$(terraform output -json)

    # Use jq to parse the output, reducing multiple calls to terraform
    GCP_PROJECT_ID=$(jq -r '.project_id.value' <<< "$TF_OUTPUT")
    GCP_REGION=$(jq -r '.region.value' <<< "$TF_OUTPUT")
    GCS_BUCKET_NAME=$(jq -r '.bucket_name.value' <<< "$TF_OUTPUT")
    ARTIFACT_REGISTRY_REPO=$(jq -r '.artifact_registry_repo.value' <<< "$TF_OUTPUT")
    JOB_NAME=$(jq -r '.job_name.value' <<< "$TF_OUTPUT")

    popd > /dev/null

    # Validate that all required variables were fetched
    if [ -z "$GCP_PROJECT_ID" ] || [ -z "$GCP_REGION" ] || [ -z "$GCS_BUCKET_NAME" ] || [ -z "$ARTIFACT_REGISTRY_REPO" ] || [ -z "$JOB_NAME" ]; then
        echo "Error: Could not fetch all required outputs from Terraform."
        echo "Please run 'terraform apply' in the 'terraform' directory first."
        exit 1
    fi
}

# 2. Build and push the container image
build() {
    fetch_infra
    local image_name="csp-comparator-pipeline" # Defining a consistent image name
    local image_uri="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REGISTRY_REPO}/${image_name}:latest"

    echo "Building and pushing container: ${image_uri}"
    gcloud builds submit --tag "${image_uri}" .

    # Persist the image URI for the deploy step
    echo "IMAGE_URI=${image_uri}" > /tmp/image_uri.tmp
}

# 3. Deploy the infrastructure using Terraform
deploy() {
    # The 'build' step must be run before 'deploy'
    if [ ! -f /tmp/image_uri.tmp ]; then
        echo "Error: Image URI not found. Please run the 'build' command first."
        exit 1
    fi
    source /tmp/image_uri.tmp

    echo "Deploying infrastructure with Terraform..."
    pushd terraform > /dev/null
    terraform apply -auto-approve \
        -var="container_image=${IMAGE_URI}"
    popd > /dev/null
}

# 4. Trigger the Cloud Run Job
trigger() {
    fetch_infra # Ensure we have the latest job name
    echo "Executing job: ${JOB_NAME}..."
    gcloud run jobs execute "${JOB_NAME}" --region "${GCP_REGION}" --args="$*"
}

# Main command dispatcher
case "$1" in
    build) build ;;
    deploy) deploy ;;
    trigger) shift; trigger "$@" ;;
    build)   fetch_infra; gcloud builds submit --tag "${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REGISTRY_REPO}/${IMAGE_NAME}:latest" --project "$GCP_PROJECT_ID" . ;;
    *) echo "Usage: source manage.sh {deploy|trigger|build}" ;;
esac
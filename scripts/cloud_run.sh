#!/bin/bash
set -e
set -o pipefail
set -u

# Function to display usage information
usage() {
    echo "Usage: $0 {build|deploy|trigger} [additional_args...]"
    echo
    echo "Commands:"
    echo "  build                          Builds the Docker container and pushes it to Artifact Registry."
    echo "  deploy                         Builds the container and deploys the infrastructure using Terraform."
    echo "  trigger [additional_args...]   Triggers the Cloud Run job with optional arguments."
    echo
    echo "Required Environment Variables:"
    echo "  GCP_PROJECT_ID                 Google Cloud Project ID."
    echo "  GCP_REGION                     GCP region for resources (e.g., us-central1)."
    echo "  GCS_BUCKET_NAME                Name for the GCS bucket."
    echo "  SERVICE_ACCOUNT_EMAIL          Service Account email to run the job as."
    echo "  ARTIFACT_REGISTRY_REPO         Name of the Artifact Registry repository."
    echo "  IMAGE_NAME                     Name of the container image."
    echo
    echo "Note: A .env file in the root directory will be sourced if it exists."
}

# Load environment variables from .env file if it exists
if [ -f "$(dirname "$0")/../.env" ]; then
    echo "Sourcing .env file..."
    set -a
    # shellcheck source=/dev/null
    source "$(dirname "$0")/../.env"
    set +a
fi

# Function to check for required environment variables
check_vars() {
    local required_vars=(
        GCP_PROJECT_ID
        GCP_REGION
        GCS_BUCKET_NAME
        SERVICE_ACCOUNT_EMAIL
        ARTIFACT_REGISTRY_REPO
        IMAGE_NAME
    )
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var-}" ]; then
            missing_vars+=("$var")
        fi
    done
    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo "Error: Missing required environment variables: ${missing_vars[*]}"
        usage
        exit 1
    fi
}

# Function to build the Docker container
build() {
    echo "Building container..."
    check_vars
    local image_uri="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REGISTRY_REPO}/${IMAGE_NAME}:latest"
    gcloud builds submit --tag "${image_uri}" .
    echo "Container built and pushed successfully: ${image_uri}"
}

# Function to deploy the infrastructure
deploy() {
    echo "Deploying infrastructure..."
    build # Always build before deploying

    local image_uri="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REGISTRY_REPO}/${IMAGE_NAME}:latest"

    cd terraform

    echo "Initializing Terraform..."
    terraform init

    echo "Applying Terraform configuration..."
    terraform apply -auto-approve \
        -var="project_id=${GCP_PROJECT_ID}" \
        -var="region=${GCP_REGION}" \
        -var="bucket_name=${GCS_BUCKET_NAME}" \
        -var="service_account_email=${SERVICE_ACCOUNT_EMAIL}" \
        -var="container_image=${image_uri}"

    echo "Deployment successful."
    cd ..
}

# Function to trigger the Cloud Run job
trigger() {
    echo "Triggering Cloud Run job..."
    check_vars
    local job_name="csp-comparator-job"
    gcloud run jobs execute "${job_name}" --region "${GCP_REGION}" --args="$*"
    echo "Job triggered."
}

# Main script logic
if [ $# -eq 0 ]; then
    usage
    exit 1
fi

case "$1" in
    build)
        build
        ;;
    deploy)
        deploy
        ;;
    trigger)
        shift # Remove the 'trigger' command itself
        trigger "$@"
        ;;
    *)
        usage
        exit 1
        ;;
esac

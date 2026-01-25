#!/bin/bash

fetch_infra() {
    echo "Querying Terraform for infrastructure details..."
    pushd terraform > /dev/null

    # Run terraform output once and capture the JSON output
    TF_OUTPUT=$(terraform output -json)

    # Use jq to parse the output, reducing multiple calls to terraform
    export GCP_PROJECT_ID=$(jq -r '.project_id.value' <<< "$TF_OUTPUT")
    export BUCKET_NAME=$(jq -r '.bucket_name.value' <<< "$TF_OUTPUT")
    export AI_LOCATION=$(jq -r '.region.value' <<< "$TF_OUTPUT")

    popd > /dev/null

    # Validate that all required variables were fetched
    if [ -z "$GCP_PROJECT_ID" ] || [ "$GCP_PROJECT_ID" == "null" ] || [ -z "$BUCKET_NAME" ] || [ -z "$AI_LOCATION" ]; then
        echo "Error: Could not fetch all required outputs from Terraform."
        echo "Please run 'terraform apply' in the 'terraform' directory first."
        return 1
    fi
}

fetch_infra

export PYTHONPATH=$PYTHONPATH:.
python3 main.py "$@"

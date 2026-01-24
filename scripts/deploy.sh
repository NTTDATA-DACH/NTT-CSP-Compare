#!/bin/bash
# This script is a wrapper around the cloud_run.sh script.
# It executes the 'deploy' command from the cloud_run.sh script.

# Get the directory of the currently executing script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Call the cloud_run.sh script with the 'deploy' argument
"${SCRIPT_DIR}/cloud_run.sh" deploy

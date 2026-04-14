#!/bin/bash

# Script to download only the thermal_logger folder from the repository
# Usage: Download this script and run it. It will download thermal_logger into the current directory.

set -e  # Exit if any command fails

# Configuration
REPO_URL="https://github.com/luquito/Fprime.git"
FOLDER_NAME="thermal_logger"

echo "Starting download of $FOLDER_NAME from repository..."

# Create a temporary directory for the sparse clone
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Navigate to temp directory and set up sparse checkout
cd "$TEMP_DIR"
git init --quiet
git remote add origin "$REPO_URL"
git config core.sparseCheckout true

# Configure sparse checkout to only get thermal_logger
echo "$FOLDER_NAME" > .git/info/sparse-checkout

# Pull only the thermal_logger folder with depth 1 for efficiency
git pull origin main --quiet --depth=1

# Check if the folder was successfully downloaded
if [ ! -d "$FOLDER_NAME" ]; then
    echo "Error: Failed to download $FOLDER_NAME from repository"
    exit 1
fi

# Get the directory where the script was run from
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Move the thermal_logger folder to the current working directory
mv "$FOLDER_NAME" "$SCRIPT_DIR/$FOLDER_NAME"

echo "✓ Successfully downloaded $FOLDER_NAME to: $SCRIPT_DIR/$FOLDER_NAME"

#!/bin/bash

# Script to download only the thermal_logger folder from the repository
# Usage: Download this script and run it. It will download thermal_logger into the current directory.

set -e  # Exit if any command fails

# Configuration
GITHUB_USER="luquito"
REPO_NAME="Fprime"
BRANCH="main"
FOLDER_NAME="thermal_logger"

echo "Starting download of $FOLDER_NAME from repository..."

# Create a temporary directory for extraction
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Download the repository as a tarball
TARBALL_URL="https://github.com/$GITHUB_USER/$REPO_NAME/archive/refs/heads/$BRANCH.tar.gz"

echo "Downloading from: $TARBALL_URL"
curl -sL "$TARBALL_URL" | tar xz -C "$TEMP_DIR"

# Navigate to the extracted folder
EXTRACTED_REPO="$TEMP_DIR/$REPO_NAME-$BRANCH"

# Check if the folder exists
if [ ! -d "$EXTRACTED_REPO/$FOLDER_NAME" ]; then
    echo "Error: Failed to find $FOLDER_NAME in repository"
    exit 1
fi

# Get the directory where the script was run from
SCRIPT_DIR="$(pwd)"

# Move the thermal_logger folder to the current working directory
mv "$EXTRACTED_REPO/$FOLDER_NAME" "$SCRIPT_DIR/$FOLDER_NAME"

echo "✓ Successfully downloaded $FOLDER_NAME to: $SCRIPT_DIR/$FOLDER_NAME"

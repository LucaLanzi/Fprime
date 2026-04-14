#!/bin/bash

# Script to download only the thermal_logger folder from the repository
# Usage: Download this script and run it. It will download thermal_logger into the current directory.

set -e  # Exit if any command fails

# Configuration
GITHUB_USER="LucaLanzi"
REPO_NAME="Fprime"
BRANCH="main"
FOLDER_PATH="python-playground/thermal_logger"
FOLDER_NAME="thermal_logger"

echo "Starting download of $FOLDER_NAME from repository..."

# Create a temporary directory for extraction
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Download the repository as a tarball
TARBALL_URL="https://github.com/$GITHUB_USER/$REPO_NAME/archive/refs/heads/$BRANCH.tar.gz"
TARBALL_FILE="$TEMP_DIR/repo.tar.gz"

echo "Downloading from: $TARBALL_URL"
if ! curl -fSL "$TARBALL_URL" -o "$TARBALL_FILE"; then
    echo "Error: Failed to download from $TARBALL_URL"
    echo "Please verify:"
    echo "  1. Repository exists and is public: https://github.com/$GITHUB_USER/$REPO_NAME"
    echo "  2. Branch name is correct: $BRANCH"
    exit 1
fi

# Verify the file was downloaded
if [ ! -f "$TARBALL_FILE" ] || [ ! -s "$TARBALL_FILE" ]; then
    echo "Error: Tarball file is empty or missing"
    exit 1
fi

# Extract the tarball
echo "Extracting archive..."
if ! tar xzf "$TARBALL_FILE" -C "$TEMP_DIR"; then
    echo "Error: Failed to extract tarball"
    exit 1
fi

# Navigate to the extracted folder
EXTRACTED_REPO="$TEMP_DIR/$REPO_NAME-$BRANCH"

# Check if the folder exists
if [ ! -d "$EXTRACTED_REPO/$FOLDER_PATH" ]; then
    echo "Error: Failed to find $FOLDER_PATH in repository"
    echo "Expected path: $EXTRACTED_REPO/$FOLDER_PATH"
    echo "Available directories:"
    ls -la "$EXTRACTED_REPO" 2>/dev/null || echo "Cannot list directory"
    exit 1
fi

# Get the current working directory
SCRIPT_DIR="$(pwd)"

# Move the thermal_logger folder to the current working directory
mv "$EXTRACTED_REPO/$FOLDER_PATH" "$SCRIPT_DIR/$FOLDER_NAME"

echo "✓ Successfully downloaded $FOLDER_NAME to: $SCRIPT_DIR/$FOLDER_NAME"

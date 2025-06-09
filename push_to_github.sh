#!/bin/bash

# Check if a commit message was provided as an argument
if [ -z "$1" ]; then
    echo "Error: No commit message provided."
    echo "Usage: ./push_to_github.sh <commit-message>"
    exit 1
fi

echo "Staging changes..."
git add .

echo "Committing changes..."
git commit -m "$1"

echo "Pushing changes to remote repository..."
git push origin main

# Print a success message if the push completes without errors
if [ $? -eq 0 ]; then
    echo "Changes pushed successfully."
else
    echo "An error occurred during push."
fi
#!/usr/bin/env bash
#
# Destroy all OTel Demo infrastructure
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "OTel Demo - Destroy"
echo "=========================================="
echo
echo "WARNING: This will destroy all AWS resources!"
echo
read -p "Are you sure? Type 'destroy' to confirm: " -r
echo

if [[ "$REPLY" != "destroy" ]]; then
    echo "Aborted."
    exit 0
fi

# Check prerequisites
command -v glab >/dev/null 2>&1 || { echo "Error: glab not found"; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "Error: aws not found"; exit 1; }

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "Error: AWS credentials not configured"
    echo "Ensure your AWS credentials are set up before destroying resources."
    exit 1
fi

# Destroy infrastructure
echo "Destroying infrastructure..."
cd "$PROJECT_ROOT"
make destroy

# Clean build artifacts
echo
echo "Cleaning build artifacts..."
make clean

echo
echo "=========================================="
echo "Destroy Complete!"
echo "=========================================="
echo
echo "All AWS resources have been destroyed."
echo "Note: S3 bucket may require manual deletion if not empty."

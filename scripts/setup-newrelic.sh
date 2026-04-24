#!/usr/bin/env bash
#
# Set up New Relic API key in SSM Parameter Store
#
set -euo pipefail

PARAM_NAME="/otel-demo/newrelic/api-key"

echo "=========================================="
echo "OTel Demo - New Relic Setup"
echo "=========================================="
echo
echo "This script stores your New Relic Ingest API key in AWS SSM Parameter Store."
echo
echo "To get your API key:"
echo "  1. Sign up or log in to New Relic: https://newrelic.com/signup (free tier available)"
echo "  2. Go to: User menu > API keys"
echo "  3. Create or copy your Ingest - License key"
echo

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "Error: AWS credentials not configured"
    echo "Ensure your AWS credentials are set up before running this script."
    exit 1
fi

# Prompt for API key
read -sp "Enter your New Relic Ingest API key: " API_KEY
echo

if [ -z "$API_KEY" ]; then
    echo "Error: API key cannot be empty"
    exit 1
fi

# Store in SSM
echo "Storing API key in SSM Parameter Store..."
aws ssm put-parameter \
    --name "$PARAM_NAME" \
    --type "SecureString" \
    --value "$API_KEY" \
    --overwrite \
    --description "New Relic Ingest API key for OTel Demo"

echo
echo "Success! API key stored at: $PARAM_NAME"
echo
echo "The consumer-newrelic Lambda will now use this key to export telemetry."

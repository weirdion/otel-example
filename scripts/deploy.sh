#!/usr/bin/env bash
#
# Deploy OTel Demo infrastructure and code
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "OTel Demo - Deploy"
echo "=========================================="

# Check prerequisites
echo "Checking prerequisites..."
command -v glab >/dev/null 2>&1 || { echo "Error: glab not found. Install from: https://gitlab.com/gitlab-org/cli"; exit 1; }
command -v tofu >/dev/null 2>&1 || { echo "Error: tofu (OpenTofu) not found. Install from: https://opentofu.org"; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "Error: aws CLI not found"; exit 1; }
command -v pip >/dev/null 2>&1 || { echo "Error: pip not found"; exit 1; }

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "Error: AWS credentials not configured"
    echo ""
    echo "Configure AWS credentials using one of:"
    echo "  - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)"
    echo "  - AWS CLI profile (aws configure)"
    echo "  - AWS SSO (aws sso login --profile <profile>)"
    echo "  - IAM role (if running on EC2/ECS/Lambda)"
    exit 1
fi

echo "Prerequisites OK"
echo

# Build layers
echo "Building Lambda layers..."
cd "$PROJECT_ROOT"
make build-layers
echo

# Initialize Tofu if needed
echo "Initializing OpenTofu..."
cd "$PROJECT_ROOT/infra"
if [ ! -d ".terraform" ]; then
    cd "$PROJECT_ROOT"
    make init
fi
echo

# Plan
echo "Planning infrastructure..."
cd "$PROJECT_ROOT"
make plan

# Prompt for confirmation
echo
read -p "Apply these changes? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Apply
echo "Applying infrastructure..."
make apply

# Get outputs
echo
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
cd "$PROJECT_ROOT/infra"
echo
echo "API Gateway URL:"
tofu output -raw api_gateway_url 2>/dev/null || echo "(run 'tofu output' in infra/ to see outputs)"
echo
echo
echo "Next steps:"
echo "  1. Set up New Relic API key: ./scripts/setup-newrelic.sh"
echo "  2. Run the simulator:"
echo "     cd simulator && npm install"
echo "     npm run simulate -- --url <API_URL> --scenario all"

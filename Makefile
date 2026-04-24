.PHONY: help init plan apply destroy fmt validate clean

# Default target
help:
	@echo "OTel Demo - Makefile"
	@echo ""
	@echo "Infrastructure targets:"
	@echo "  init      - Initialize OpenTofu with GitLab-managed state"
	@echo "  re-init   - Re-initialize with -reconfigure"
	@echo "  plan      - Plan infrastructure changes"
	@echo "  apply     - Apply infrastructure changes"
	@echo "  destroy   - Destroy all infrastructure"
	@echo ""
	@echo "Code quality:"
	@echo "  fmt       - Format all OpenTofu files"
	@echo "  validate  - Validate OpenTofu configuration"
	@echo ""
	@echo "Development:"
	@echo "  build-layer   - Build the OTel Lambda layer"
	@echo "  build-lambdas - Build all Lambda functions"
	@echo "  test          - Run all tests"
	@echo ""
	@echo "Utilities:"
	@echo "  clean     - Clean build artifacts"
	@echo ""
	@echo "Requirements:"
	@echo "  - glab CLI (>= 1.66) - https://gitlab.com/gitlab-org/cli"
	@echo "  - OpenTofu (>= 1.6) - https://opentofu.org"
	@echo "  - AWS CLI with valid credentials"
	@echo ""
	@echo "Usage:"
	@echo "  # Configure AWS credentials (choose one method):"
	@echo "  # - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
	@echo "  # - AWS profile: aws configure"
	@echo "  # - AWS SSO: aws sso login --profile <your-profile>"
	@echo ""
	@echo "  make init && make plan"

# Directories
INFRA_DIR := infra
ENV_DIR := $(INFRA_DIR)/environments/dev

# Tools
TF := tofu
GLAB := glab

# State name for GitLab
STATE_NAME := otel-demo

# Check dependencies
check-glab:
	@which $(GLAB) > /dev/null || (echo "Error: glab CLI not found. Install from: https://gitlab.com/gitlab-org/cli" && exit 1)

check-aws:
	@aws sts get-caller-identity > /dev/null 2>&1 || (echo "Error: AWS credentials not configured. See 'make help' for options." && exit 1)

# tfvars file (copy from .example if not exists)
TFVARS_FILE := $(INFRA_DIR)/environments/dev/terraform.tfvars
TFVARS_EXAMPLE := $(TFVARS_FILE).example

check-tfvars:
	@if [ ! -f "$(TFVARS_FILE)" ]; then \
		echo "Error: $(TFVARS_FILE) not found"; \
		echo "Create it from the example:"; \
		echo "  cp $(TFVARS_EXAMPLE) $(TFVARS_FILE)"; \
		exit 1; \
	fi

# Infrastructure targets
init: check-glab check-tfvars
	@echo "Initializing OpenTofu with GitLab-managed state..."
	$(GLAB) opentofu -d $(INFRA_DIR) init $(STATE_NAME) -- -var-file=environments/dev/terraform.tfvars

re-init: check-glab check-tfvars
	@echo "Re-initializing OpenTofu with GitLab-managed state..."
	$(GLAB) opentofu -d $(INFRA_DIR) init $(STATE_NAME) -- -reconfigure -var-file=environments/dev/terraform.tfvars

plan: check-glab check-aws check-tfvars
	@echo "Planning infrastructure changes..."
	$(GLAB) opentofu -d $(INFRA_DIR) plan $(STATE_NAME) -- -var-file=environments/dev/terraform.tfvars

apply: check-glab check-aws check-tfvars
	@echo "Applying infrastructure changes..."
	$(GLAB) opentofu -d $(INFRA_DIR) apply $(STATE_NAME) -- -var-file=environments/dev/terraform.tfvars

destroy: check-glab check-aws check-tfvars
	@echo "Destroying all infrastructure..."
	$(GLAB) opentofu -d $(INFRA_DIR) destroy $(STATE_NAME) -- -var-file=environments/dev/terraform.tfvars

# Code quality
fmt:
	@echo "Formatting OpenTofu files..."
	$(TF) fmt -recursive $(INFRA_DIR)

validate: check-glab
	@echo "Validating OpenTofu configuration..."
	cd $(INFRA_DIR) && $(TF) validate

# Build targets
build-layers: build-otel-layer build-runtime-layer
	@echo "All layers built successfully"

build-otel-layer:
	@echo "Building OTel Lambda layer..."
	rm -rf layers/otel-common/python/otel_common/__pycache__ 2>/dev/null || true
	pip install -r layers/otel-common/requirements.txt -t layers/otel-common/python/ --upgrade --quiet

build-runtime-layer:
	@echo "Building runtime dependencies layer..."
	rm -rf layers/runtime-deps/python/* 2>/dev/null || true
	pip install -r layers/runtime-deps/requirements.txt -t layers/runtime-deps/python/ --upgrade --quiet
	@echo "Runtime layer size: $$(du -sh layers/runtime-deps/python | cut -f1)"

# Note: Lambda functions only contain handler code, deps come from layers
build-lambdas:
	@echo "Lambda functions use layers for dependencies - no build needed"
	@echo "Run 'make build-layers' to build dependency layers"

# Test targets
test:
	@echo "Running tests..."
	cd backend && python -m pytest tests/ -v

# Clean
clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name ".terraform" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".build" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".terraform.lock.hcl" -delete 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.zip" -delete 2>/dev/null || true
	find layers/otel-common/python -mindepth 1 -maxdepth 1 ! -name 'otel_common' -exec rm -rf {} + 2>/dev/null || true
	rm -rf layers/runtime-deps/python/* 2>/dev/null || true
	touch layers/runtime-deps/python/.gitkeep
	@echo "Clean complete"

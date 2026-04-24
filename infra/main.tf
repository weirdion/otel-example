# =============================================================================
# OTel Demo - Main Infrastructure
# =============================================================================

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# -----------------------------------------------------------------------------
# Core Infrastructure Modules
# -----------------------------------------------------------------------------

module "s3" {
  source = "./modules/s3"

  name_prefix    = local.name_prefix
  retention_days = var.s3_retention_days
}

module "kinesis" {
  source = "./modules/kinesis"

  name_prefix     = local.name_prefix
  retention_hours = var.kinesis_retention_hours
}

# -----------------------------------------------------------------------------
# Lambda Layer for OTel Instrumentation
# -----------------------------------------------------------------------------

module "otel_layer" {
  source = "./modules/otel-layer"

  name_prefix = local.name_prefix
}

# -----------------------------------------------------------------------------
# Lambda Functions
# -----------------------------------------------------------------------------

module "lambda_user_actions" {
  source = "./modules/lambda"

  name_prefix               = local.name_prefix
  function_name             = "user-actions"
  handler                   = "handler.handler"
  source_dir                = "${path.root}/../backend/functions/user_actions"
  layers                    = [module.otel_layer.layer_arn]
  kinesis_stream_arn        = module.kinesis.stream_arn
  cloudwatch_retention_days = var.cloudwatch_retention_days

  environment_variables = {
    KINESIS_STREAM_NAME = module.kinesis.stream_name
    POWERTOOLS_SERVICE_NAME = "user-actions"
    POWERTOOLS_METRICS_NAMESPACE = var.project_name
    LOG_LEVEL = "INFO"
  }
}

module "lambda_order_service" {
  source = "./modules/lambda"

  name_prefix               = local.name_prefix
  function_name             = "order-service"
  handler                   = "handler.handler"
  source_dir                = "${path.root}/../backend/functions/order_service"
  layers                    = [module.otel_layer.layer_arn]
  kinesis_stream_arn        = module.kinesis.stream_arn
  cloudwatch_retention_days = var.cloudwatch_retention_days

  environment_variables = {
    KINESIS_STREAM_NAME = module.kinesis.stream_name
    POWERTOOLS_SERVICE_NAME = "order-service"
    POWERTOOLS_METRICS_NAMESPACE = var.project_name
    LOG_LEVEL = "INFO"
  }
}

# -----------------------------------------------------------------------------
# Kinesis Consumers
# -----------------------------------------------------------------------------

module "consumer_s3" {
  source = "./modules/lambda"

  name_prefix               = local.name_prefix
  function_name             = "consumer-s3"
  handler                   = "handler.handler"
  source_dir                = "${path.root}/../backend/functions/consumer_s3"
  layers                    = []
  kinesis_stream_arn        = module.kinesis.stream_arn
  cloudwatch_retention_days = var.cloudwatch_retention_days
  is_kinesis_consumer       = true

  environment_variables = {
    AUDIT_BUCKET_NAME = module.s3.bucket_name
    POWERTOOLS_SERVICE_NAME = "consumer-s3"
    LOG_LEVEL = "INFO"
  }

  additional_policies = [module.s3.write_policy_arn]
}

module "consumer_newrelic" {
  source = "./modules/lambda"

  name_prefix               = local.name_prefix
  function_name             = "consumer-newrelic"
  handler                   = "handler.handler"
  source_dir                = "${path.root}/../backend/functions/consumer_newrelic"
  layers                    = []
  kinesis_stream_arn        = module.kinesis.stream_arn
  cloudwatch_retention_days = var.cloudwatch_retention_days
  is_kinesis_consumer       = true

  environment_variables = {
    NEWRELIC_ACCOUNT_ID = var.newrelic_account_id
    POWERTOOLS_SERVICE_NAME = "consumer-newrelic"
    LOG_LEVEL = "INFO"
  }
}

# -----------------------------------------------------------------------------
# API Gateway
# -----------------------------------------------------------------------------

module "api_gateway" {
  source = "./modules/api-gateway"

  name_prefix = local.name_prefix

  lambda_integrations = {
    user_actions = {
      lambda_arn         = module.lambda_user_actions.function_arn
      lambda_invoke_arn  = module.lambda_user_actions.invoke_arn
      routes = [
        { method = "POST", path = "/actions" },
        { method = "GET",  path = "/actions/{id}" },
      ]
    }
    order_service = {
      lambda_arn         = module.lambda_order_service.function_arn
      lambda_invoke_arn  = module.lambda_order_service.invoke_arn
      routes = [
        { method = "POST", path = "/orders" },
        { method = "GET",  path = "/orders/{id}" },
      ]
    }
  }
}

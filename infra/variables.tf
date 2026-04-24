variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-2"
}

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "otel-demo"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "kinesis_retention_hours" {
  description = "Kinesis data stream retention period in hours"
  type        = number
  default     = 24
}

variable "s3_retention_days" {
  description = "S3 object retention period in days for audit logs"
  type        = number
  default     = 30
}

variable "cloudwatch_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 7
}

variable "newrelic_account_id" {
  description = "New Relic account ID for telemetry export"
  type        = string
  default     = ""
}

variable "newrelic_api_key" {
  description = "New Relic Ingest API key (stored in SSM Parameter Store)"
  type        = string
  default     = ""
  sensitive   = true
}

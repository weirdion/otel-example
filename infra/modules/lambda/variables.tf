variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "handler" {
  description = "Lambda handler (e.g., handler.handler)"
  type        = string
  default     = "handler.handler"
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.13"
}

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 30
}

variable "memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 256
}

variable "source_dir" {
  description = "Directory containing Lambda source code"
  type        = string
}

variable "layers" {
  description = "List of Lambda layer ARNs"
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "Environment variables for the Lambda function"
  type        = map(string)
  default     = {}
}

variable "cloudwatch_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "kinesis_stream_arn" {
  description = "ARN of the Kinesis stream (for write access or consumer)"
  type        = string
  default     = ""
}

variable "is_kinesis_consumer" {
  description = "Whether this Lambda consumes from Kinesis"
  type        = bool
  default     = false
}

variable "kinesis_batch_size" {
  description = "Kinesis event source batch size"
  type        = number
  default     = 100
}

variable "additional_policies" {
  description = "List of additional IAM policy ARNs to attach"
  type        = list(string)
  default     = []
}

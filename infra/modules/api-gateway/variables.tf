variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "lambda_integrations" {
  description = "Map of Lambda integrations with their routes"
  type = map(object({
    lambda_arn        = string
    lambda_invoke_arn = string
    routes = list(object({
      method = string
      path   = string
    }))
  }))
}

variable "cors_allow_origins" {
  description = "CORS allowed origins"
  type        = list(string)
  default     = ["*"]
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

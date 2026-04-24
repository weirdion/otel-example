variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "retention_days" {
  description = "Number of days to retain telemetry objects"
  type        = number
  default     = 30
}

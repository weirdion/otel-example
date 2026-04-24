variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "retention_hours" {
  description = "Number of hours to retain data in the stream"
  type        = number
  default     = 24
}

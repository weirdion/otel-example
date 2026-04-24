variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "compatible_runtimes" {
  description = "Compatible Lambda runtimes"
  type        = list(string)
  default     = ["python3.11", "python3.12", "python3.13"]
}

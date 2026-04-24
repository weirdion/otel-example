output "layer_arn" {
  description = "ARN of the runtime dependencies Lambda layer"
  value       = aws_lambda_layer_version.runtime.arn
}

output "layer_version" {
  description = "Version of the runtime dependencies Lambda layer"
  value       = aws_lambda_layer_version.runtime.version
}

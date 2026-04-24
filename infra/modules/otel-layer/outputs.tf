output "layer_arn" {
  description = "ARN of the OTel Lambda layer"
  value       = aws_lambda_layer_version.otel.arn
}

output "layer_version" {
  description = "Version of the OTel Lambda layer"
  value       = aws_lambda_layer_version.otel.version
}

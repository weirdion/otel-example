output "kinesis_stream_arn" {
  description = "ARN of the Kinesis data stream for telemetry"
  value       = module.kinesis.stream_arn
}

output "kinesis_stream_name" {
  description = "Name of the Kinesis data stream"
  value       = module.kinesis.stream_name
}

output "audit_bucket_name" {
  description = "Name of the S3 bucket for audit logs"
  value       = module.s3.bucket_name
}

output "audit_bucket_arn" {
  description = "ARN of the S3 bucket for audit logs"
  value       = module.s3.bucket_arn
}

output "api_gateway_url" {
  description = "URL of the API Gateway endpoint"
  value       = module.api_gateway.api_url
}

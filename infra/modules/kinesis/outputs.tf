output "stream_arn" {
  description = "ARN of the Kinesis data stream"
  value       = aws_kinesis_stream.telemetry.arn
}

output "stream_name" {
  description = "Name of the Kinesis data stream"
  value       = aws_kinesis_stream.telemetry.name
}

output "write_policy_arn" {
  description = "ARN of the IAM policy for writing to the stream"
  value       = aws_iam_policy.write.arn
}

output "read_policy_arn" {
  description = "ARN of the IAM policy for reading from the stream"
  value       = aws_iam_policy.read.arn
}

output "bucket_name" {
  description = "Name of the audit S3 bucket"
  value       = aws_s3_bucket.audit.id
}

output "bucket_arn" {
  description = "ARN of the audit S3 bucket"
  value       = aws_s3_bucket.audit.arn
}

output "write_policy_arn" {
  description = "ARN of the IAM policy for writing to the bucket"
  value       = aws_iam_policy.write.arn
}

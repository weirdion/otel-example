# =============================================================================
# S3 Module - Audit Bucket for Telemetry
# =============================================================================

resource "aws_s3_bucket" "audit" {
  bucket = "${var.name_prefix}-audit-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "${var.name_prefix}-audit"
  }
}

resource "aws_s3_bucket_versioning" "audit" {
  bucket = aws_s3_bucket.audit.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "audit" {
  bucket = aws_s3_bucket.audit.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id

  rule {
    id     = "expire-old-telemetry"
    status = "Enabled"

    filter {
      prefix = "telemetry/"
    }

    expiration {
      days = var.retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
}

# IAM policy for Lambda to write to this bucket
resource "aws_iam_policy" "write" {
  name        = "${var.name_prefix}-s3-audit-write"
  description = "Allow writing telemetry to the audit S3 bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = "${aws_s3_bucket.audit.arn}/telemetry/*"
      }
    ]
  })
}

# Data source for account ID
data "aws_caller_identity" "current" {}

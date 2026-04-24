aws_region  = "us-east-2"
environment = "dev"

# Retention policies (shorter for dev/learning)
kinesis_retention_hours   = 24
s3_retention_days         = 30
cloudwatch_retention_days = 7

# New Relic (set these after creating your account)
# newrelic_account_id = "YOUR_ACCOUNT_ID"
# newrelic_api_key    = ""  # Use SSM Parameter Store instead

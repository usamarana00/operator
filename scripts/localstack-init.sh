#!/bin/bash
# Creates the S3 bucket in LocalStack on startup
awslocal s3 mb s3://freelance-agent-dev
awslocal s3api put-bucket-cors --bucket freelance-agent-dev --cors-configuration '{
  "CORSRules": [{
    "AllowedOrigins": ["http://localhost:3000"],
    "AllowedMethods": ["GET", "PUT", "DELETE"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"]
  }]
}'
echo "LocalStack S3 bucket ready"

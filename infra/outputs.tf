output "backend_url" {
  description = "App Runner backend service URL"
  value       = "https://${aws_apprunner_service.backend.service_url}"
}

output "ecr_repository_url" {
  description = "ECR repository URL — used in CI/CD docker push"
  value       = aws_ecr_repository.backend.repository_url
}

output "aurora_endpoint" {
  description = "Aurora cluster writer endpoint"
  value       = aws_rds_cluster.aurora.endpoint
  sensitive   = true
}

output "aurora_secret_arn" {
  description = "Secrets Manager ARN for Aurora master password"
  value       = aws_rds_cluster.aurora.master_user_secret[0].secret_arn
  sensitive   = true
}

output "sqs_ingestion_url" {
  description = "SQS ingestion queue URL"
  value       = aws_sqs_queue.ingestion.url
}

output "sqs_escalation_url" {
  description = "SQS escalation queue URL"
  value       = aws_sqs_queue.escalation.url
}

output "vector_bucket_name" {
  description = "S3 Vectors bucket name"
  value       = aws_s3vectors_vector_bucket.papers.vector_bucket_name
}

output "sagemaker_endpoint_name" {
  description = "SageMaker embedding endpoint name — set as SAGEMAKER_ENDPOINT env var"
  value       = aws_sagemaker_endpoint.embeddings.name
}

output "frontend_url" {
  description = "CloudFront URL for the LivePaper frontend"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "frontend_bucket" {
  description = "S3 bucket name — upload Next.js export here"
  value       = aws_s3_bucket.frontend.bucket
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID — needed for cache invalidation after deploy"
  value       = aws_cloudfront_distribution.frontend.id
}

output "ci_access_key_id" {
  description = "AWS_ACCESS_KEY_ID for GitHub Actions secrets"
  value       = aws_iam_access_key.ci.id
}

output "ci_secret_access_key" {
  description = "AWS_SECRET_ACCESS_KEY for GitHub Actions secrets"
  value       = aws_iam_access_key.ci.secret
  sensitive   = true
}

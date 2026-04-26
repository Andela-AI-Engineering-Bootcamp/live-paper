# ── S3 Vector Bucket ──────────────────────────────────────────────────────────
# Created manually via CLI — Terraform AWS provider does not yet support
# aws_s3vectors_vector_bucket. Bucket name: livepaper-vectors, index: papers.
# ARN: arn:aws:s3vectors:us-east-1:375510692572:bucket/livepaper-vectors

locals {
  vector_bucket_name = "${var.app_name}-vectors"
  vector_bucket_arn  = "arn:aws:s3vectors:${var.aws_region}:${data.aws_caller_identity.current.account_id}:bucket/${var.app_name}-vectors"
}

# ── IAM — allow App Runner task role to read/write vectors ────────────────────

data "aws_iam_policy_document" "s3vectors_access" {
  statement {
    actions = [
      "s3vectors:PutVectors",
      "s3vectors:QueryVectors",
      "s3vectors:GetVectors",
      "s3vectors:DeleteVectors",
    ]
    resources = [
      local.vector_bucket_arn,
      "${local.vector_bucket_arn}/*",
    ]
  }
}

resource "aws_iam_policy" "s3vectors_access" {
  name   = "${var.app_name}-s3vectors-access"
  policy = data.aws_iam_policy_document.s3vectors_access.json
}

# ── S3 bucket for raw PDF storage ────────────────────────────────────────────

resource "aws_s3_bucket" "papers_raw" {
  bucket = "${var.app_name}-papers-raw-293184993462"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "papers_raw" {
  bucket = aws_s3_bucket.papers_raw.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "papers_raw" {
  bucket                  = aws_s3_bucket.papers_raw.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ── IAM — allow App Runner task role to read/write raw PDFs ──────────────────

data "aws_iam_policy_document" "papers_raw_access" {
  statement {
    actions   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.papers_raw.arn}/*"]
  }
  statement {
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.papers_raw.arn]
  }
}

resource "aws_iam_policy" "papers_raw_access" {
  name   = "${var.app_name}-papers-raw-accessyes"
  policy = data.aws_iam_policy_document.papers_raw_access.json
}

# ── IAM — CI user for GitHub Actions (ECR push + S3 deploy) ──────────────────

resource "aws_iam_user" "ci" {
  name = "${var.app_name}-ci"
}

resource "aws_iam_access_key" "ci" {
  user = aws_iam_user.ci.name
}

data "aws_iam_policy_document" "ci_access" {
  statement {
    actions = [
      "ecr:GetAuthorizationToken",
      "ecr:BatchCheckLayerAvailability",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage",
      # buildx HEADs the manifest before push to dedupe; that maps to BatchGetImage.
      # DescribeImages keeps `docker buildx imagetools inspect` style calls happy.
      "ecr:BatchGetImage",
      "ecr:DescribeImages",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "ci_ecr" {
  name   = "${var.app_name}-ci-ecr"
  policy = data.aws_iam_policy_document.ci_access.json
}

resource "aws_iam_user_policy_attachment" "ci_ecr" {
  user       = aws_iam_user.ci.name
  policy_arn = aws_iam_policy.ci_ecr.arn
}

resource "aws_iam_user_policy_attachment" "ci_frontend_deploy" {
  user       = aws_iam_user.ci.name
  policy_arn = aws_iam_policy.frontend_deploy.arn
}

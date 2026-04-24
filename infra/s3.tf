# ── S3 Vector Bucket ──────────────────────────────────────────────────────────
# AWS S3 Vectors stores 384-dim all-MiniLM embeddings.
# One index: "papers" — stores paper chunk embeddings + metadata.

resource "aws_s3vectors_vector_bucket" "papers" {
  vector_bucket_name = "${var.app_name}-vectors"
}

resource "aws_s3vectors_index" "papers" {
  vector_bucket_name = aws_s3vectors_vector_bucket.papers.vector_bucket_name
  index_name         = "papers"
  data_type          = "float32"
  dimension          = 384  # all-MiniLM-L6-v2 output dimension
  distance_metric    = "cosine"
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
      aws_s3vectors_vector_bucket.papers.arn,
      "${aws_s3vectors_vector_bucket.papers.arn}/*",
    ]
  }
}

resource "aws_iam_policy" "s3vectors_access" {
  name   = "${var.app_name}-s3vectors-access"
  policy = data.aws_iam_policy_document.s3vectors_access.json
}

# ── S3 bucket for raw PDF storage ────────────────────────────────────────────

resource "aws_s3_bucket" "papers_raw" {
  bucket = "${var.app_name}-papers-raw"
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
  name   = "${var.app_name}-papers-raw-access"
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

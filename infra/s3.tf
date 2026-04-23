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

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "app_name" {
  description = "Application name prefix for all resources"
  type        = string
  default     = "livepaper"
}

variable "aurora_db_name" {
  description = "Aurora Serverless v2 database name"
  type        = string
  default     = "livepaper"
}

variable "aurora_username" {
  description = "Aurora master username"
  type        = string
  default     = "livepaper"
}

variable "aurora_min_acu" {
  description = "Aurora Serverless v2 minimum ACUs (0.5 = pause when idle)"
  type        = number
  default     = 0.5
}

variable "aurora_max_acu" {
  description = "Aurora Serverless v2 maximum ACUs"
  type        = number
  default     = 4
}

variable "sagemaker_model_image" {
  description = "ECR image URI for the SageMaker embedding model (all-MiniLM-L6-v2)"
  type        = string
  # Uses HuggingFace DLC — replace with your own if needed
  default     = "763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-inference:2.1.0-transformers4.37.0-cpu-py310-ubuntu22.04"
}

variable "sagemaker_max_concurrency" {
  description = "SageMaker Serverless max concurrent invocations"
  type        = number
  default     = 5
}

variable "backend_image_tag" {
  description = "ECR image tag deployed to App Runner"
  type        = string
  default     = "latest"
}

variable "langfuse_public_key" {
  description = "LangFuse public key (stored in Secrets Manager)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "langfuse_secret_key" {
  description = "LangFuse secret key (stored in Secrets Manager)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "openai_api_key" {
  description = "OpenAI API key (stored in Secrets Manager)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "neo4j_uri" {
  description = "Neo4J Aura connection URI (leave empty to skip graph writes)"
  type        = string
  default     = ""
}

variable "neo4j_username" {
  description = "Neo4J username"
  type        = string
  default     = "neo4j"
}

variable "neo4j_password" {
  description = "Neo4J password (stored in Secrets Manager)"
  type        = string
  sensitive   = true
  default     = ""
}

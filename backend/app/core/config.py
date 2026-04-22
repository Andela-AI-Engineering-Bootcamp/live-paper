"""Application settings — loaded from environment / .env file.

Pattern from zeya-antenatal: pydantic_settings with production validator
that fails loudly on missing secrets rather than silently misbehaving.
"""

import warnings
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "LivePaper API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api"
    CORS_ORIGINS: str = "http://localhost:3000"

    # AI
    OPENAI_API_KEY: str = ""
    BEDROCK_MODEL_ID: str = "us.amazon.nova-pro-v1:0"
    BEDROCK_REGION: str = "us-west-2"

    # LangFuse
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # AWS
    AWS_REGION: str = "us-east-1"

    # Storage
    AURORA_CLUSTER_ARN: str = ""
    AURORA_SECRET_ARN: str = ""
    AURORA_DATABASE: str = "livepaper"
    VECTOR_BUCKET: str = ""
    SAGEMAKER_ENDPOINT: str = "livepaper-embedding-endpoint"

    # Queues
    SQS_INGESTION_QUEUE_URL: str = ""
    SQS_ESCALATION_QUEUE_URL: str = ""

    # Graph
    NEO4J_URI: str = ""
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # Retrieval
    GAP_CONFIDENCE_THRESHOLD: float = 0.55

    model_config = {"env_file": ".env", "case_sensitive": True}

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.DEBUG:
            return self

        missing = [
            name
            for name, val in {
                "OPENAI_API_KEY": self.OPENAI_API_KEY,
                "AURORA_CLUSTER_ARN": self.AURORA_CLUSTER_ARN,
                "VECTOR_BUCKET": self.VECTOR_BUCKET,
                "NEO4J_URI": self.NEO4J_URI,
                "NEO4J_PASSWORD": self.NEO4J_PASSWORD,
                "SQS_INGESTION_QUEUE_URL": self.SQS_INGESTION_QUEUE_URL,
            }.items()
            if not val
        ]
        if missing:
            raise ValueError(f"Missing required secrets for production: {', '.join(missing)}")

        if not self.LANGFUSE_PUBLIC_KEY:
            warnings.warn("LANGFUSE_PUBLIC_KEY not set — agent traces will not be recorded.")

        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


settings = Settings()

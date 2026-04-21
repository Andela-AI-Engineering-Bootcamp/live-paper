"""Shared agent setup — LiteLLM model + LangFuse tracing.

All five agents import get_model() from here so model config and
observability are configured in one place, not five.

Pattern from Alex course: LiteLLM routes to Bedrock, OpenAI, or any
provider without changing agent code.
"""

import logging
import os

from agents.extensions.models.litellm_model import LitellmModel
from langfuse import Langfuse

logger = logging.getLogger(__name__)

_langfuse: Langfuse | None = None


def get_model() -> LitellmModel:
    """Return a LiteLLM model configured for the active provider.

    Reads BEDROCK_MODEL_ID and BEDROCK_REGION from environment.
    Falls back to gpt-4o-mini if Bedrock credentials are absent (dev mode).
    """
    bedrock_model = os.getenv("BEDROCK_MODEL_ID", "")
    bedrock_region = os.getenv("BEDROCK_REGION", "us-west-2")

    if bedrock_model:
        os.environ["AWS_REGION_NAME"] = bedrock_region
        return LitellmModel(model=f"bedrock/{bedrock_model}")

    logger.warning("BEDROCK_MODEL_ID not set — falling back to gpt-4o-mini")
    return LitellmModel(model="gpt-4o-mini")


def get_langfuse() -> Langfuse | None:
    """Return the shared LangFuse client, or None if keys are not set."""
    global _langfuse
    if _langfuse is not None:
        return _langfuse

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not public_key or not secret_key:
        logger.warning("LangFuse keys not set — tracing disabled")
        return None

    _langfuse = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
    return _langfuse

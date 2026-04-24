"""Vector storage service — AWS S3 Vectors (same bucket pattern as Alex).

Wraps the s3vectors client for storing and querying paper embeddings.
Falls back to an in-memory store when VECTOR_BUCKET is not set (dev mode).
"""

import logging
import os
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

_memory_store: dict[str, dict] = {}  # dev fallback


async def store_embedding(
    text: str,
    vector: list[float],
    metadata: dict,
    paper_id: Optional[str] = None,
) -> str:
    """Store an embedding with metadata. Returns the vector ID."""
    vector_id = paper_id or str(uuid.uuid4())
    bucket = os.getenv("VECTOR_BUCKET", "")

    if not bucket:
        _memory_store[vector_id] = {"text": text, "vector": vector, "metadata": metadata}
        logger.debug("Dev mode: stored embedding in memory for %s", vector_id)
        return vector_id

    try:
        import boto3
        client = boto3.client("s3vectors", region_name=os.getenv("AWS_REGION", "us-east-1"))
        client.put_vectors(
            vectorBucketName=bucket,
            indexName=os.getenv("VECTOR_INDEX", "papers"),
            vectors=[{
                "key": vector_id,
                "data": {"float32": vector},
                "metadata": metadata,
            }],
        )
        return vector_id
    except Exception as exc:
        logger.error("S3 Vectors store failed: %s", exc)
        raise


async def query_similar(
    vector: list[float],
    top_k: int = 5,
    filter_metadata: Optional[dict] = None,
) -> list[dict]:
    """Return top-k most similar vectors with metadata and scores."""
    bucket = os.getenv("VECTOR_BUCKET", "")

    if not bucket:
        # Dev mode: cosine similarity against memory store
        return _memory_cosine_search(vector, top_k)

    try:
        import boto3
        client = boto3.client("s3vectors", region_name=os.getenv("AWS_REGION", "us-east-1"))
        response = client.query_vectors(
            vectorBucketName=bucket,
            indexName=os.getenv("VECTOR_INDEX", "papers"),
            queryVector={"float32": vector},
            topK=top_k,
            returnMetadata=True,
        )
        return response.get("vectors", [])
    except Exception as exc:
        logger.error("S3 Vectors query failed: %s", exc)
        raise


def _memory_cosine_search(query: list[float], top_k: int) -> list[dict]:
    """Cosine similarity search over the in-memory dev store."""
    import math

    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        return dot / (norm_a * norm_b + 1e-8)

    scored = [
        {"key": k, "score": cosine(query, v["vector"]), "metadata": v["metadata"]}
        for k, v in _memory_store.items()
    ]
    return sorted(scored, key=lambda x: x["score"], reverse=True)[:top_k]

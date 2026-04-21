"""API key validation dependency.

LivePaper uses API keys for inter-service calls (Lambda → API) and
Bearer tokens for frontend requests. Swap for JWT/Clerk in production.
"""

import os
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str = Security(_api_key_header)) -> str:
    """Validate X-API-Key header. Returns key if valid, raises 401 otherwise."""
    expected = os.getenv("INTERNAL_API_KEY", "dev-key")
    if not api_key or api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key

"""Shared test fixtures — pattern from zeya-antenatal."""

import os
import pytest
from httpx import AsyncClient, ASGITransport

# Force dev mode — no real AWS/Neo4J calls in tests
os.environ["DEBUG"] = "true"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["VECTOR_BUCKET"] = ""   # use in-memory store
os.environ["NEO4J_URI"] = ""       # use no-op graph
os.environ["SAGEMAKER_ENDPOINT"] = ""  # use local fallback

from app.factory import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

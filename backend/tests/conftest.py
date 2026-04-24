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
from app.services.database import init_db


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    # ASGITransport doesn't fire FastAPI lifespan events, so the dev-mode
    # SQLite tables that the live app creates in lifespan would not exist.
    # Initialize them explicitly here so the test fixtures behave like prod.
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

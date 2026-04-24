"""Shared test fixtures — pattern from zeya-antenatal."""

import hashlib
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
from app.services import embeddings as embed_svc
from app.services.database import init_db


# Tests should not need sentence-transformers (heavy: pulls in torch). We stub
# `embed` with a deterministic 384-d vector derived from a SHA-256 of the input.
# Same input → same vector, different inputs → different vectors, so similarity
# search behaves consistently. This also keeps the production `_local_embed`
# strict: in real code a missing model raises rather than poisoning S3 Vectors
# with a zero vector.
async def _fake_embed(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    repeats = (384 // len(digest)) + 1
    raw = (digest * repeats)[:384]
    return [(b - 128) / 128.0 for b in raw]


@pytest.fixture(autouse=True)
def _stub_embeddings(monkeypatch):
    monkeypatch.setattr(embed_svc, "embed", _fake_embed)


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

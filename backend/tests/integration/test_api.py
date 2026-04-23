"""Integration tests — hit the actual FastAPI app with ASGI transport."""

import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "graph_nodes" in data


@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "livepaper-api"


@pytest.mark.asyncio
async def test_ingest_requires_pdf_url_or_manual_fields(client):
    # Empty body — missing both pdf_url and manual fields
    response = await client.post("/api/papers/ingest", json={})
    assert response.status_code == 422  # Pydantic validation error

    # title without abstract — still invalid
    response = await client.post("/api/papers/ingest", json={"title": "A Paper"})
    assert response.status_code == 422

    # manual path with both required fields — valid
    response = await client.post(
        "/api/papers/ingest",
        json={"title": "A Paper", "abstract": "This paper studies X."},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ingest_returns_job_id(client):
    response = await client.post(
        "/api/papers/ingest",
        json={"pdf_url": "https://example.com/paper.pdf"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_ask_returns_result(client):
    response = await client.post(
        "/api/search/ask",
        json={"question": "What is artemisinin used for?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "passages" in data
    assert "escalated" in data


@pytest.mark.asyncio
async def test_job_not_found(client):
    response = await client.get("/api/papers/jobs/nonexistent-id")
    assert response.status_code == 404

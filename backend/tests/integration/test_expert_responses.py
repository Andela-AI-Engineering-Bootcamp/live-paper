"""Integration tests for the expert-response and expert-invite endpoints."""

import pytest

from app.services import database as db


@pytest.fixture(autouse=True)
def _frontend_url(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://test.example.com")


@pytest.mark.asyncio
async def test_submit_expert_response_404_when_paper_missing(client):
    response = await client.post(
        "/api/expert-responses",
        json={
            "paper_id": "does-not-exist",
            "expert_email": "alice@example.com",
            "response": "Some insight.",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_submit_expert_response_persists_everything(client):
    # Seed a paper directly so we don't have to wait for ingestion to complete
    await db.create_paper(
        paper_id="paper-test-1",
        title="Test paper",
        authors=["Author A"],
        abstract="Abstract.",
        status="completed",
    )

    response = await client.post(
        "/api/expert-responses",
        json={
            "paper_id": "paper-test-1",
            "expert_email": "alice@example.com",
            "response": "This paper's methodology is sound but section 3 omits the control group.",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    assert body["paper_id"] == "paper-test-1"
    assert body["expert_email"] == "alice@example.com"

    experts_response = await client.get("/api/experts")
    assert experts_response.status_code == 200
    experts = experts_response.json()
    assert any(e["email"] == "alice@example.com" for e in experts), experts


@pytest.mark.asyncio
async def test_invite_expert_returns_link(client):
    await db.create_paper(
        paper_id="paper-test-invite",
        title="Invite test",
        authors=["Author B"],
        abstract="Abstract.",
        status="completed",
    )

    response = await client.post(
        "/api/papers/paper-test-invite/invite-expert",
        json={
            "expert_email": "bob+filter@example.com",
            "expert_name": "Dr. Bob",
            "affiliation": "MIT",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["paper_id"] == "paper-test-invite"
    assert body["expert_email"] == "bob+filter@example.com"
    assert body["invite_url"].startswith("https://test.example.com/expert-response?")
    assert "paper_id=paper-test-invite" in body["invite_url"]
    # Ensure the email is URL-encoded (the + must be escaped)
    assert "bob%2Bfilter%40example.com" in body["invite_url"]


@pytest.mark.asyncio
async def test_invite_expert_404_when_paper_missing(client):
    response = await client.post(
        "/api/papers/missing/invite-expert",
        json={"expert_email": "carol@example.com"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_invite_expert_500_when_frontend_url_missing(client, monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "")

    await db.create_paper(
        paper_id="paper-no-fronturl",
        title="No URL",
        authors=[],
        abstract="",
        status="completed",
    )

    response = await client.post(
        "/api/papers/paper-no-fronturl/invite-expert",
        json={"expert_email": "dan@example.com"},
    )
    assert response.status_code == 500

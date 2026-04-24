"""Experts endpoint — list registered experts and their associated papers."""

import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/experts", tags=["experts"])

# In-memory store — populated by the response ingestion agent
# Keys are expert names; values mirror the Expert ORM model
_experts: dict[str, dict] = {}


@router.get("")
async def list_experts() -> list[dict]:
    return list(_experts.values())


@router.get("/{expert_id}")
async def get_expert(expert_id: str) -> dict:
    if expert_id not in _experts:
        raise HTTPException(status_code=404, detail="Expert not found")
    return _experts[expert_id]


def register_expert(expert_id: str, name: str, email: str | None, affiliation: str | None, papers: list[str]) -> None:
    """Called by the response ingestion agent when an expert submits an answer."""
    existing = _experts.get(expert_id, {})
    _experts[expert_id] = {
        "id": expert_id,
        "name": name,
        "email": email or existing.get("email"),
        "affiliation": affiliation or existing.get("affiliation"),
        "bio": existing.get("bio", ""),
        "papers": list(set(existing.get("papers", []) + papers)),
    }

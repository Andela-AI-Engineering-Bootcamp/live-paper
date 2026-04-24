"""Experts endpoint — list registered experts and their associated papers.

Backed by Aurora; experts are populated by:
  - response_ingestion agent when an expert submits an escalation answer
  - POST /api/expert-responses when an expert submits a paper-level review
  - POST /api/papers/{id}/invite-expert when an admin creates an invite
"""

import logging
from fastapi import APIRouter, HTTPException

from app.services import database as db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/experts", tags=["experts"])


@router.get("")
async def list_experts() -> list[dict]:
    return await db.list_experts()


@router.get("/{expert_id}")
async def get_expert(expert_id: str) -> dict:
    expert = await db.get_expert(expert_id)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")
    return expert

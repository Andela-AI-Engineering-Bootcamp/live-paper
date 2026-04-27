"""Experts endpoint — list registered experts and their associated papers."""

import logging
from typing import Optional
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, HTTPException

from app.services import database as db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/experts", tags=["experts"])


class AddExpertRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    paper_id: Optional[str] = None


@router.get("")
async def list_experts() -> list[dict]:
    return await db.list_experts()


@router.post("", status_code=201)
async def add_expert(payload: AddExpertRequest) -> dict:
    """
    Create or update an expert record then optionally link them to a paper.
    Uses upsert_expert so duplicate emails are handled gracefully.
    """
    # upsert_expert finds by email or creates — returns the expert id
    expert_id = await db.upsert_expert(
        email=payload.email,
        name=payload.name or None,
    )

    # Associate paper if provided
    if payload.paper_id:
        paper = await db.get_paper(payload.paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        await db.associate_expert_paper(
            expert_id=expert_id,
            paper_id=payload.paper_id,
        )

    # Return the full expert record with papers
    expert = await db.get_expert(expert_id)
    if not expert:
        raise HTTPException(status_code=500, detail="Failed to retrieve expert after creation")
    return expert


@router.get("/{expert_id}")
async def get_expert(expert_id: str) -> dict:
    expert = await db.get_expert(expert_id)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")
    return expert
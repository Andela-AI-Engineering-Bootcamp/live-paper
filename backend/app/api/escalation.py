"""Escalation endpoint — ingest an expert's response into the knowledge base."""

import logging
from fastapi import APIRouter, HTTPException

from app.agents import response_ingestion
from app.models.paper import ExpertResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/escalation", tags=["escalation"])


@router.post("/respond")
async def ingest_expert_response(response: ExpertResponse, question: str) -> dict:
    """Ingest an expert response and write it to the knowledge graph."""
    try:
        vector_id = await response_ingestion.run(response, question)
        return {
            "status": "ingested",
            "vector_id": vector_id,
            "expert": response.expert_name,
            "message": "Expert response added to knowledge base. Future queries will use this answer.",
        }
    except Exception as exc:
        logger.error("Failed to ingest expert response: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

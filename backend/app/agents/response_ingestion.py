"""Response Ingestion Agent — embeds an expert reply into the knowledge base.

When an expert responds, this agent:
1. Validates the response as an ExpertResponse Pydantic model
2. Embeds the response text via SageMaker
3. Stores the embedding in S3 Vectors (attributed to expert + source paper)
4. Writes an ExpertResponse node to Neo4J linked to the source Paper

After ingestion, the next user who asks the same question gets the
expert's answer instantly — no LLM call needed.
"""

import logging

from app.agents.base import get_langfuse
from app.models.paper import ExpertResponse
from app.services import database as db
from app.services import embeddings as embed_svc
from app.services import graph, storage

logger = logging.getLogger(__name__)


async def run(response: ExpertResponse, question: str) -> str:
    """Ingest an expert response. Returns the vector ID of the stored embedding."""
    lf = get_langfuse()
    trace_obj = lf.trace(
        name="response-ingestion",
        input={"expert": response.expert_name, "paper": response.source_paper_id},
    ) if lf else None

    try:
        vector = await embed_svc.embed(response.response_text)
        vector_id = f"expert-{response.source_paper_id}-{response.expert_name[:20]}"

        await storage.store_embedding(
            text=response.response_text,
            vector=vector,
            metadata={
                "type": "expert_response",
                "expert": response.expert_name,
                "affiliation": response.affiliation or "",
                "paper_id": response.source_paper_id,
                "question": question,
            },
            paper_id=vector_id,
        )

        await graph.write_expert_response(
            paper_id=response.source_paper_id,
            expert_name=response.expert_name,
            response_text=response.response_text,
            question=question,
        )

        # Populate Aurora so the experts list and the future expert-response
        # endpoint can both see this person. Email-less experts (the legacy
        # escalation flow doesn't require one) get a synthetic local-part so
        # the upsert key still exists; real flows pass a proper address.
        synthetic_email = f"{response.expert_name.lower().replace(' ', '.')}@unknown.local"
        expert_id = await db.upsert_expert(
            email=synthetic_email,
            name=response.expert_name,
            affiliation=response.affiliation,
            is_registered=True,
        )
        await db.create_expert_response(
            paper_id=response.source_paper_id,
            expert_id=expert_id,
            question=question,
            response_text=response.response_text,
            vector_id=vector_id,
        )

        if trace_obj:
            trace_obj.update(output={"vector_id": vector_id}, status="success")

        logger.info(
            "Expert response from %s ingested as %s", response.expert_name, vector_id
        )
        return vector_id

    except Exception as exc:
        if trace_obj:
            trace_obj.update(status="error", error=str(exc))
        logger.error("Response ingestion failed: %s", exc)
        raise

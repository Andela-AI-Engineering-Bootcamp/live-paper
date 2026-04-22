from fastapi import APIRouter
from app.services import graph

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    node_count = await graph.get_node_count()
    return {"status": "ok", "service": "livepaper-api", "graph_nodes": node_count}

"""Neo4J knowledge graph service.

Writes concept, paper, expert, and response nodes.
Falls back to a no-op logger when NEO4J_URI is not set (dev mode).
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        uri = os.getenv("NEO4J_URI", "").strip()
        if not uri:
            return None
        try:
            from neo4j import GraphDatabase
            _driver = GraphDatabase.driver(
                uri,
                auth=(os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
            )
        except Exception as exc:
            logger.warning("Neo4J driver init failed: %s — running without graph", exc)
            return None
    return _driver


async def write_paper_node(paper_id: str, metadata: dict) -> None:
    """Create or update a Paper node in the knowledge graph."""
    driver = _get_driver()
    if not driver:
        logger.debug("Dev mode: skipping Neo4J write for paper %s", paper_id)
        return
    with driver.session() as session:
        session.run(
            """
            MERGE (p:Paper {id: $id})
            SET p += $props
            """,
            id=paper_id,
            props={**metadata, "id": paper_id},
        )


async def write_concept_nodes(paper_id: str, concepts: list[str]) -> None:
    """Create Concept nodes and link them to a Paper."""
    driver = _get_driver()
    if not driver:
        logger.debug("Dev mode: skipping concept nodes for paper %s", paper_id)
        return
    with driver.session() as session:
        for concept in concepts:
            session.run(
                """
                MERGE (c:Concept {name: $concept})
                WITH c
                MATCH (p:Paper {id: $paper_id})
                MERGE (p)-[:COVERS]->(c)
                """,
                concept=concept,
                paper_id=paper_id,
            )


async def write_expert_response(
    paper_id: str,
    expert_name: str,
    response_text: str,
    question: str,
) -> None:
    """Create an ExpertResponse node linked to the source Paper."""
    driver = _get_driver()
    if not driver:
        logger.debug("Dev mode: skipping expert response node")
        return
    with driver.session() as session:
        session.run(
            """
            MATCH (p:Paper {id: $paper_id})
            CREATE (r:ExpertResponse {
                expert: $expert,
                text: $text,
                question: $question,
                created_at: datetime()
            })
            CREATE (p)-[:HAS_RESPONSE]->(r)
            """,
            paper_id=paper_id,
            expert=expert_name,
            text=response_text,
            question=question,
        )


async def get_node_count() -> int:
    """Return total node count — shown in demo to prove graph is growing."""
    driver = _get_driver()
    if not driver:
        return 0
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) AS count")
        return result.single()["count"]

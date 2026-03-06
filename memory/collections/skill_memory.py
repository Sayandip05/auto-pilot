"""
memory/collections/skill_memory.py
Manages the skill_memory ChromaDB collection.
Stores learned patterns, API quirks, and DOM paths discovered during execution.
"""

from __future__ import annotations
import uuid
import asyncio
import structlog
from memory.chroma_client import get_collection

logger = structlog.get_logger()
COLLECTION_NAME = "skill_memory"


def _col():
    return get_collection(COLLECTION_NAME)


async def store(skill_name: str, content: str, metadata: dict = None) -> str:
    """Store a learned skill pattern."""
    def _write():
        doc_id = str(uuid.uuid4())
        _col().add(
            documents=[content],
            metadatas=[{"skill": skill_name, **(metadata or {})}],
            ids=[doc_id],
        )
        return doc_id

    doc_id = await asyncio.get_event_loop().run_in_executor(None, _write)
    logger.info("skill_memory.stored", skill=skill_name)
    return doc_id


async def query(skill_name: str, query_text: str, top_k: int = 3) -> list[dict]:
    """Retrieve relevant skill patterns for a given skill and query."""
    def _read():
        results = _col().query(
            query_texts=[query_text],
            n_results=top_k,
            where={"skill": skill_name},
        )
        return [
            {
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
            }
            for i in range(len(results["documents"][0]))
        ]

    return await asyncio.get_event_loop().run_in_executor(None, _read)

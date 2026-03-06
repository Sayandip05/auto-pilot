"""
memory/collections/user_preferences.py
Manages the user_preferences ChromaDB collection.
Stores learned preferences, habits, and patterns per user.
"""

from __future__ import annotations
import uuid
import asyncio
import structlog
from memory.chroma_client import get_collection

logger = structlog.get_logger()
COLLECTION_NAME = "user_preferences"


def _col():
    return get_collection(COLLECTION_NAME)


async def store(user_key: str, content: str, metadata: dict = None) -> str:
    """Store a new user preference. Returns the document ID."""
    def _write():
        doc_id = str(uuid.uuid4())
        _col().add(
            documents=[content],
            metadatas=[{"user_key": user_key, **(metadata or {})}],
            ids=[doc_id],
        )
        return doc_id

    doc_id = await asyncio.get_event_loop().run_in_executor(None, _write)
    logger.info("preferences.stored", user=user_key, doc_id=doc_id)
    return doc_id


async def query(user_key: str, query_text: str, top_k: int = 5) -> list[dict]:
    """Semantic search over stored preferences for a user."""
    def _read():
        results = _col().query(
            query_texts=[query_text],
            n_results=top_k,
            where={"user_key": user_key},
        )
        return [
            {
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            }
            for i in range(len(results["documents"][0]))
        ]

    return await asyncio.get_event_loop().run_in_executor(None, _read)


async def delete(doc_id: str) -> bool:
    """Delete a preference by document ID."""
    def _del():
        _col().delete(ids=[doc_id])

    await asyncio.get_event_loop().run_in_executor(None, _del)
    return True

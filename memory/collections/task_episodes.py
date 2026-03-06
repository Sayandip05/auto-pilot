"""
memory/collections/task_episodes.py
Manages the task_episodes ChromaDB collection.
Stores full context of completed tasks for future retrieval and learning.
"""

from __future__ import annotations
import uuid
import asyncio
import structlog
from memory.chroma_client import get_collection

logger = structlog.get_logger()
COLLECTION_NAME = "task_episodes"


def _col():
    return get_collection(COLLECTION_NAME)


async def store(
    task_id: str,
    workflow: str,
    user_key: str,
    summary: str,
    outcome: str,
    extra_metadata: dict = None,
) -> str:
    """Store a completed task episode."""
    content = f"Workflow: {workflow}\nSummary: {summary}\nOutcome: {outcome}"

    def _write():
        doc_id = task_id or str(uuid.uuid4())
        _col().upsert(
            documents=[content],
            metadatas=[{
                "task_id": task_id,
                "workflow": workflow,
                "user_key": user_key,
                "outcome": outcome,
                **(extra_metadata or {}),
            }],
            ids=[doc_id],
        )
        return doc_id

    doc_id = await asyncio.get_event_loop().run_in_executor(None, _write)
    logger.info("episodes.stored", task_id=task_id, workflow=workflow)
    return doc_id


async def query(user_key: str, query_text: str, top_k: int = 3) -> list[dict]:
    """Retrieve past task episodes similar to the given query."""
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
            }
            for i in range(len(results["documents"][0]))
        ]

    return await asyncio.get_event_loop().run_in_executor(None, _read)

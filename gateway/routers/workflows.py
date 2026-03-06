"""gateway/routers/workflows.py — trigger, query, and manage workflows."""

import uuid
import structlog
import httpx
import os

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Any

from routers.auth import verify_token

logger = structlog.get_logger()
router = APIRouter()

AGENTS_URL = os.getenv("AGENTS_URL", "http://agents:8001")

VALID_WORKFLOWS = {
    "email_to_calendar",
    "slack_to_notion",
    "price_tracker",
    "file_organizer",
    "social_poster",
}


class WorkflowTrigger(BaseModel):
    workflow_type: str
    input_data: dict = {}
    stream: bool = False


class WorkflowResponse(BaseModel):
    task_id: str
    status: str
    message: str


class MemoryQueryRequest(BaseModel):
    collection: str
    query: str
    top_k: int = 5
    user_key: Optional[str] = None


async def dispatch_to_agents(task_id: str, workflow_type: str, input_data: dict, user_key: str):
    """Fire-and-forget: send task to the agent engine."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            await client.post(
                f"{AGENTS_URL}/tasks",
                json={
                    "task_id": task_id,
                    "workflow_type": workflow_type,
                    "input_data": input_data,
                    "user_key": user_key,
                },
            )
    except Exception as e:
        logger.error("workflow.dispatch_failed", task_id=task_id, error=str(e))


@router.post("/trigger", response_model=WorkflowResponse)
async def trigger_workflow(
    body: WorkflowTrigger,
    background_tasks: BackgroundTasks,
    payload: dict = Depends(verify_token),
):
    if body.workflow_type not in VALID_WORKFLOWS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown workflow '{body.workflow_type}'. Valid: {sorted(VALID_WORKFLOWS)}",
        )

    task_id = str(uuid.uuid4())
    user_key = payload.get("sub", "unknown")

    logger.info(
        "workflow.triggered",
        task_id=task_id,
        workflow=body.workflow_type,
        user=user_key,
    )

    background_tasks.add_task(
        dispatch_to_agents, task_id, body.workflow_type, body.input_data, user_key
    )

    return WorkflowResponse(
        task_id=task_id,
        status="accepted",
        message=f"Workflow '{body.workflow_type}' queued ✅ (Task #{task_id[:8]})",
    )


@router.get("/stats")
async def get_workflow_stats(payload: dict = Depends(verify_token)):
    """Return task count statistics from the agent engine."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{AGENTS_URL}/tasks/stats")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    # Fallback stats if agent engine is unreachable
    return {"total": 0, "completed": 0, "running": 0, "failed": 0, "pending": 0}


@router.get("/")
async def list_workflows(
    payload: dict = Depends(verify_token),
    status: Optional[str] = Query(None),
    workflow_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """List tasks from the agent engine with optional filters."""
    try:
        params = {"limit": limit}
        if status:
            params["status"] = status
        if workflow_type:
            params["workflow_type"] = workflow_type

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{AGENTS_URL}/tasks", params=params)
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.error("workflow.list_error", error=str(e))

    return {"tasks": [], "workflows": sorted(VALID_WORKFLOWS)}


@router.get("/list")
async def list_workflow_types(payload: dict = Depends(verify_token)):
    """List available workflow types."""
    return {"workflows": sorted(VALID_WORKFLOWS)}


@router.get("/{task_id}/status")
async def get_task_status(task_id: str, payload: dict = Depends(verify_token)):
    """Query the agent engine for task status."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{AGENTS_URL}/tasks/{task_id}")
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail="Task not found")
            return resp.json()
    except HTTPException:
        raise
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Agent engine unavailable")


@router.get("/{task_id}")
async def get_task(task_id: str, payload: dict = Depends(verify_token)):
    """Get full task details by ID."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{AGENTS_URL}/tasks/{task_id}")
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail="Task not found")
            return resp.json()
    except HTTPException:
        raise
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Agent engine unavailable")


@router.post("/memory/query")
async def query_memory(body: MemoryQueryRequest, payload: dict = Depends(verify_token)):
    """Semantic search over ChromaDB memory collections."""
    user_key = body.user_key or payload.get("sub", "default")

    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agents", "specialists"))
        from memory_agent import query_preferences, query_episodes

        if body.collection == "user_preferences":
            result = await query_preferences({"query": body.query, "user_key": user_key, "top_k": body.top_k})
            return {"memories": result.get("memories", [])}

        elif body.collection == "task_episodes":
            result = await query_episodes({"query": body.query, "user_key": user_key, "top_k": body.top_k})
            return {"memories": result.get("episodes", [])}

        else:
            return {"memories": [], "note": f"Collection '{body.collection}' not queryable via this endpoint"}

    except Exception as e:
        logger.error("workflow.memory_query_error", error=str(e))
        return {"memories": [], "error": str(e)}

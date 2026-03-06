"""gateway/routers/webhooks.py — inbound webhooks from Gmail, Slack, Telegram."""

import hmac
import hashlib
import structlog
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import os

logger = structlog.get_logger()
router = APIRouter()


@router.post("/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Telegram sends updates here when webhook mode is enabled."""
    data = await request.json()
    logger.info("webhook.telegram", update_id=data.get("update_id"))
    # The Telegram bot handler processes this asynchronously
    # For now just acknowledge receipt
    return {"ok": True}


@router.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """Slack Events API — verify signature then process event."""
    body_bytes = await request.body()
    signing_secret = os.getenv("SLACK_SIGNING_SECRET", "")

    # Verify Slack signature
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    slack_signature = request.headers.get("X-Slack-Signature", "")
    sig_basestring = f"v0:{timestamp}:{body_bytes.decode()}"
    mac = hmac.new(signing_secret.encode(), sig_basestring.encode(), hashlib.sha256)
    computed = "v0=" + mac.hexdigest()

    if not hmac.compare_digest(computed, slack_signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    data = await request.json()

    # Respond to URL verification challenge
    if data.get("type") == "url_verification":
        return {"challenge": data["challenge"]}

    logger.info("webhook.slack_event", event_type=data.get("event", {}).get("type"))
    # TODO: dispatch to agent engine for slack_to_notion workflow
    return JSONResponse({"ok": True})


@router.post("/gmail/push")
async def gmail_push(request: Request):
    """Gmail push notification — triggers email_to_calendar workflow."""
    data = await request.json()
    logger.info("webhook.gmail_push")
    # TODO: decode Gmail push notification and dispatch to agent engine
    return {"ok": True}

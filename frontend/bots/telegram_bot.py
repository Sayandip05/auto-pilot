"""
frontend/bots/telegram_bot.py
Primary user interface — receives natural language commands via Telegram
and forwards them to the API Gateway.
"""

from __future__ import annotations
import asyncio
import os
import httpx
import structlog
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logger = structlog.get_logger()

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Map Telegram user IDs to gateway API keys (simple approach)
# In production, use /auth/register flow
USER_API_KEYS: dict[int, str] = {}


async def _post_gateway(endpoint: str, data: dict, api_key: str) -> dict:
    """POST to the API Gateway and return JSON response."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{GATEWAY_URL}{endpoint}",
            json=data,
            headers={"X-API-Key": api_key},
        )
        resp.raise_for_status()
        return resp.json()


def _get_api_key(user_id: int) -> str | None:
    return USER_API_KEYS.get(user_id)


# ── Handlers ──────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message and registration."""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hey {user.first_name}! I'm Auto-Pilot.\n\n"
        "To get started, register with:\n"
        "  /register <your-api-key>\n\n"
        "Available commands:\n"
        "  /track <url> — Track a product price\n"
        "  /emails — Check recent emails\n"
        "  /organise — Organise your Downloads folder\n"
        "  /tasks — List your Notion tasks\n"
        "  /post <text> — Schedule a social post\n"
        "  /status <task_id> — Check task status\n"
        "  /help — Show this message"
    )


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register a user with their API key."""
    if not context.args:
        await update.message.reply_text("Usage: /register <your-api-key>")
        return

    api_key = context.args[0]
    user_id = update.effective_user.id

    # Validate with gateway
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{GATEWAY_URL}/auth/validate",
                headers={"X-API-Key": api_key},
            )
        if resp.status_code == 200:
            USER_API_KEYS[user_id] = api_key
            await update.message.reply_text("✅ Registered! You're all set.")
        else:
            await update.message.reply_text("❌ Invalid API key. Check your key and try again.")
    except Exception as e:
        logger.error("telegram.register_error", error=str(e))
        await update.message.reply_text("⚠️ Could not reach the gateway. Is it running?")


async def track_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track a product price."""
    user_id = update.effective_user.id
    api_key = _get_api_key(user_id)
    if not api_key:
        await update.message.reply_text("Please /register first.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /track <product-url> [alert-price]")
        return

    url = context.args[0]
    threshold = float(context.args[1]) if len(context.args) > 1 else None

    await update.message.reply_text(f"⏳ Setting up price tracker for:\n{url}")

    try:
        result = await _post_gateway(
            "/workflows/trigger",
            {"workflow_type": "price_tracker", "input_data": {"url": url, "alert_threshold": threshold}},
            api_key,
        )
        task_id = result.get("task_id", "unknown")
        await update.message.reply_text(
            f"✅ Price tracking started!\nTask ID: `{task_id}`\n"
            f"I'll notify you when the price changes.",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("telegram.track_price_error", error=str(e))
        await update.message.reply_text(f"❌ Error: {e}")


async def check_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check recent emails."""
    user_id = update.effective_user.id
    api_key = _get_api_key(user_id)
    if not api_key:
        await update.message.reply_text("Please /register first.")
        return

    await update.message.reply_text("📧 Checking your emails...")

    try:
        result = await _post_gateway(
            "/workflows/trigger",
            {"workflow_type": "email_to_calendar", "input_data": {}},
            api_key,
        )
        response_text = result.get("response", "Emails processed.")
        await update.message.reply_text(f"📬 {response_text}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def organise_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Organise Downloads folder."""
    user_id = update.effective_user.id
    api_key = _get_api_key(user_id)
    if not api_key:
        await update.message.reply_text("Please /register first.")
        return

    await update.message.reply_text("📁 Organising your Downloads folder...")

    try:
        result = await _post_gateway(
            "/workflows/trigger",
            {"workflow_type": "file_organizer", "input_data": {}},
            api_key,
        )
        response_text = result.get("response", "Files organised.")
        await update.message.reply_text(f"✅ {response_text}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List Notion tasks."""
    user_id = update.effective_user.id
    api_key = _get_api_key(user_id)
    if not api_key:
        await update.message.reply_text("Please /register first.")
        return

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{GATEWAY_URL}/workflows/tasks",
                headers={"X-API-Key": api_key},
            )
            data = resp.json()

        tasks = data.get("tasks", [])
        if not tasks:
            await update.message.reply_text("No tasks found.")
            return

        lines = ["📋 *Your Tasks:*"]
        for t in tasks[:10]:
            lines.append(f"• {t.get('title', 'Untitled')} — {t.get('status', '')}")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def post_social(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Schedule a social post."""
    user_id = update.effective_user.id
    api_key = _get_api_key(user_id)
    if not api_key:
        await update.message.reply_text("Please /register first.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /post <text to post>")
        return

    text = " ".join(context.args)
    try:
        result = await _post_gateway(
            "/workflows/trigger",
            {"workflow_type": "social_poster", "input_data": {"text": text, "platform": "twitter"}},
            api_key,
        )
        await update.message.reply_text(f"✅ Post queued!\n\n_{text}_", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check task status by ID."""
    if not context.args:
        await update.message.reply_text("Usage: /status <task_id>")
        return

    user_id = update.effective_user.id
    api_key = _get_api_key(user_id)
    if not api_key:
        await update.message.reply_text("Please /register first.")
        return

    task_id = context.args[0]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{GATEWAY_URL}/workflows/{task_id}",
                headers={"X-API-Key": api_key},
            )
            data = resp.json()

        status = data.get("status", "unknown")
        emoji = {"completed": "✅", "running": "⏳", "failed": "❌", "pending": "🕐"}.get(status, "❓")
        await update.message.reply_text(
            f"{emoji} Task `{task_id}`\nStatus: *{status}*",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle free-form natural language messages."""
    user_id = update.effective_user.id
    api_key = _get_api_key(user_id)
    if not api_key:
        await update.message.reply_text("Please /register first to use Auto-Pilot.")
        return

    text = update.message.text.lower()

    # Simple intent detection
    if "track" in text and ("price" in text or "amazon" in text or "http" in text):
        await update.message.reply_text("It looks like you want to track a price. Use:\n/track <url> [optional-alert-price]")
    elif "email" in text or "gmail" in text:
        await check_emails(update, context)
    elif "organis" in text or "organiz" in text or "file" in text or "download" in text:
        await organise_files(update, context)
    elif "task" in text or "notion" in text:
        await list_tasks(update, context)
    elif "post" in text or "tweet" in text or "twitter" in text:
        await update.message.reply_text("To post to social media, use:\n/post <your message>")
    else:
        await update.message.reply_text(
            "I didn't understand that. Try:\n"
            "  /track <url> — Price tracking\n"
            "  /emails — Check Gmail\n"
            "  /organise — Organise files\n"
            "  /tasks — List Notion tasks\n"
            "  /post <text> — Social post\n"
            "  /help — All commands"
        )


# ── Main ──────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("track", track_price))
    app.add_handler(CommandHandler("emails", check_emails))
    app.add_handler(CommandHandler("organise", organise_files))
    app.add_handler(CommandHandler("organize", organise_files))
    app.add_handler(CommandHandler("tasks", list_tasks))
    app.add_handler(CommandHandler("post", post_social))
    app.add_handler(CommandHandler("status", check_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("telegram_bot.starting")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

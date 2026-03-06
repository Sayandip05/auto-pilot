"""
frontend/bots/discord_bot.py
Team/community interface — same capabilities as the Telegram bot
but inside Discord servers.
"""

from __future__ import annotations
import os
import httpx
import structlog
import discord
from discord.ext import commands

logger = structlog.get_logger()

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Map Discord user IDs to API keys
USER_API_KEYS: dict[int, str] = {}


def _get_api_key(user_id: int) -> str | None:
    return USER_API_KEYS.get(user_id)


async def _post_gateway(endpoint: str, data: dict, api_key: str) -> dict:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{GATEWAY_URL}{endpoint}",
            json=data,
            headers={"X-API-Key": api_key},
        )
        resp.raise_for_status()
        return resp.json()


@bot.event
async def on_ready():
    logger.info("discord_bot.ready", user=str(bot.user))
    print(f"Auto-Pilot Discord bot ready as {bot.user}")


@bot.command(name="register")
async def register(ctx, api_key: str = ""):
    """Register your API key: !register <api-key>"""
    if not api_key:
        await ctx.reply("Usage: `!register <your-api-key>`")
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{GATEWAY_URL}/auth/validate",
                headers={"X-API-Key": api_key},
            )
        if resp.status_code == 200:
            USER_API_KEYS[ctx.author.id] = api_key
            await ctx.reply("✅ Registered! You're all set.")
        else:
            await ctx.reply("❌ Invalid API key.")
    except Exception as e:
        await ctx.reply(f"⚠️ Could not reach gateway: {e}")


@bot.command(name="track")
async def track_price(ctx, url: str = "", threshold: float = None):
    """Track a product price: !track <url> [alert-price]"""
    api_key = _get_api_key(ctx.author.id)
    if not api_key:
        await ctx.reply("Please `!register` first.")
        return
    if not url:
        await ctx.reply("Usage: `!track <product-url> [optional-threshold]`")
        return

    await ctx.reply(f"⏳ Setting up price tracker for: {url}")
    try:
        result = await _post_gateway(
            "/workflows/trigger",
            {"workflow_type": "price_tracker", "input_data": {"url": url, "alert_threshold": threshold}},
            api_key,
        )
        task_id = result.get("task_id", "unknown")
        await ctx.reply(f"✅ Tracking started! Task ID: `{task_id}`")
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="emails")
async def check_emails(ctx):
    """Check recent Gmail: !emails"""
    api_key = _get_api_key(ctx.author.id)
    if not api_key:
        await ctx.reply("Please `!register` first.")
        return

    await ctx.reply("📧 Checking emails...")
    try:
        result = await _post_gateway(
            "/workflows/trigger",
            {"workflow_type": "email_to_calendar", "input_data": {}},
            api_key,
        )
        await ctx.reply(f"📬 {result.get('response', 'Emails processed.')}")
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="organise")
async def organise_files(ctx):
    """Organise Downloads folder: !organise"""
    api_key = _get_api_key(ctx.author.id)
    if not api_key:
        await ctx.reply("Please `!register` first.")
        return

    await ctx.reply("📁 Organising your Downloads...")
    try:
        result = await _post_gateway(
            "/workflows/trigger",
            {"workflow_type": "file_organizer", "input_data": {}},
            api_key,
        )
        await ctx.reply(f"✅ {result.get('response', 'Done.')}")
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="tasks")
async def list_tasks(ctx):
    """List Notion tasks: !tasks"""
    api_key = _get_api_key(ctx.author.id)
    if not api_key:
        await ctx.reply("Please `!register` first.")
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
            await ctx.reply("No tasks found.")
            return

        lines = ["📋 **Your Tasks:**"]
        for t in tasks[:10]:
            lines.append(f"• {t.get('title', 'Untitled')} — {t.get('status', '')}")
        await ctx.reply("\n".join(lines))
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="post")
async def post_social(ctx, *, text: str = ""):
    """Post to social media: !post <text>"""
    api_key = _get_api_key(ctx.author.id)
    if not api_key:
        await ctx.reply("Please `!register` first.")
        return
    if not text:
        await ctx.reply("Usage: `!post <text to tweet>`")
        return

    try:
        await _post_gateway(
            "/workflows/trigger",
            {"workflow_type": "social_poster", "input_data": {"text": text, "platform": "twitter"}},
            api_key,
        )
        await ctx.reply(f"✅ Post queued!\n> {text}")
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="status")
async def check_status(ctx, task_id: str = ""):
    """Check task status: !status <task_id>"""
    if not task_id:
        await ctx.reply("Usage: `!status <task_id>`")
        return

    api_key = _get_api_key(ctx.author.id)
    if not api_key:
        await ctx.reply("Please `!register` first.")
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{GATEWAY_URL}/workflows/{task_id}",
                headers={"X-API-Key": api_key},
            )
            data = resp.json()
        status = data.get("status", "unknown")
        emoji = {"completed": "✅", "running": "⏳", "failed": "❌", "pending": "🕐"}.get(status, "❓")
        await ctx.reply(f"{emoji} Task `{task_id}` — **{status}**")
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="autopilot")
async def help_cmd(ctx):
    """Show all commands: !autopilot"""
    await ctx.reply(
        "**Auto-Pilot Commands**\n"
        "`!register <key>` — Register your API key\n"
        "`!track <url>` — Track a product price\n"
        "`!emails` — Check Gmail\n"
        "`!organise` — Organise Downloads folder\n"
        "`!tasks` — List Notion tasks\n"
        "`!post <text>` — Post to social media\n"
        "`!status <id>` — Check task status\n"
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("DISCORD_BOT_TOKEN not set in environment")
    logger.info("discord_bot.starting")
    bot.run(BOT_TOKEN)


if __name__ == "__main__":
    main()

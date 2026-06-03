import os
import logging
import httpx
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    filters
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN_PLACEHOLDER")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

# HTTP Client Helper
async def make_post_request(endpoint: str, data: dict):
    async with httpx.AsyncClient() as client:
        url = f"{BACKEND_URL}{endpoint}"
        try:
            response = await client.post(url, json=data, timeout=20.0)
            return response.status_code, response.json()
        except Exception as e:
            logger.error(f"HTTP POST failed to {url}: {str(e)}")
            return 500, {"detail": "Failed to connect to backend server"}

async def make_get_request(endpoint: str):
    async with httpx.AsyncClient() as client:
        url = f"{BACKEND_URL}{endpoint}"
        try:
            response = await client.get(url, timeout=15.0)
            return response.status_code, response.json()
        except Exception as e:
            logger.error(f"HTTP GET failed to {url}: {str(e)}")
            return 500, []

async def make_delete_request(endpoint: str):
    async with httpx.AsyncClient() as client:
        url = f"{BACKEND_URL}{endpoint}"
        try:
            response = await client.delete(url, timeout=15.0)
            return response.status_code, response.json()
        except Exception as e:
            logger.error(f"HTTP DELETE failed to {url}: {str(e)}")
            return 500, {"detail": "Failed to connect to backend server"}


# Command Handlers

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    logger.info(f"Start command received from chat_id {chat_id}")
    
    # Register user in backend DB
    status, result = await make_post_request("/api/telegram/users", {"chat_id": chat_id})
    
    if status in [200, 201]:
        greeting = (
            "⚡ <b>Welcome to SoleSentry Pro!</b> ⚡\n\n"
            "You have been successfully registered for real-time sneaker price drop alerts!\n"
            "Whenever prices drop to or below your target thresholds, you'll receive a notification here.\n\n"
            "<b>Available Commands:</b>\n"
            "📝 `/track <url> <target_price> [size]` - Track a new sneaker (Default Size: US 9.5)\n"
            "📋 `/watchlist` - View your currently tracked sneakers\n"
            "❌ `/untrack <sneaker_id>` - Stop tracking a sneaker\n"
            "🔄 `/refresh` - Force an immediate price check on all items\n"
            "ℹ️ `/help` - View this command listing"
        )
    else:
        greeting = (
            "⚠️ <b>Connection Alert</b>\n\n"
            "Successfully connected to the bot, but could not register your Chat ID with the backend database. "
            "Please check that the FastAPI server is running."
        )
        
    await update.message.reply_text(greeting, parse_mode="HTML")


async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        usage = (
            "⚠️ <b>Invalid Command Format</b>\n\n"
            "<b>Usage:</b> `/track <url> <target_price> [size]`\n"
            "<b>Example:</b> `/track https://www.nike.com/... 140 10.5`"
        )
        await update.message.reply_text(usage, parse_mode="HTML")
        return
        
    url = args[0]
    try:
        target_price = float(args[1])
    except ValueError:
        await update.message.reply_text("❌ Target price must be a valid number!")
        return
        
    size = args[2] if len(args) > 2 else "9.5"
    
    await update.message.reply_text("⏳ Analyzing product page details... Please wait.")
    
    # Send track request to API
    status, result = await make_post_request("/api/sneakers", {
        "url": url,
        "target_price": target_price,
        "size": size
    })
    
    if status == 201:
        success_msg = (
            f"✅ <b>Successfully Tracked!</b>\n\n"
            f"👟 <b>Name:</b> {result['name']}\n"
            f"🏷️ <b>Brand:</b> {result['brand']}\n"
            f"🏪 <b>Store:</b> {result['store']}\n"
            f"📏 <b>Size Watched:</b> US {result['size']}\n"
            f"💰 <b>Retail Price:</b> ₹{result['original_price']:.2f}\n"
            f"🎯 <b>Target Alert Price:</b> ₹{result['target_price']:.2f}\n"
            f"🆔 <b>Track ID:</b> <code>{result['id']}</code>"
        )
    else:
        detail = result.get("detail", "An unexpected error occurred.")
        success_msg = f"❌ <b>Tracking Failed</b>\n\nReason: {detail}"
        
    await update.message.reply_text(success_msg, parse_mode="HTML")


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status, sneakers = await make_get_request("/api/sneakers")
    
    if status != 200:
        await update.message.reply_text("❌ Could not retrieve watchlist from backend.")
        return
        
    if not sneakers:
        empty_msg = (
            "📋 <b>Your Watchlist is empty!</b>\n\n"
            "Start tracking prices using the `/track` command:\n"
            "`/track <url> <target_price> [size]`"
        )
        await update.message.reply_text(empty_msg, parse_mode="HTML")
        return
        
    text = "📋 <b>Active Watchlist:</b>\n\n"
    for i, s in enumerate(sneakers, 1):
        status_emoji = "🟢" if s["status"] == "Dropped" else ("🔴" if s["status"] == "Increased" else "⚪")
        mode_char = "⚡" if s["updates_type"] == "Live Scraper" else "🤖"
        
        text += (
            f"{i}. <b>{s['name']}</b> (US {s['size']})\n"
            f"   Current: <b>₹{s['current_price']:.2f}</b> | Target: <b>₹{s['target_price']:.2f}</b> {status_emoji}\n"
            f"   Store: {s['store']} {mode_char} | ID: <code>{s['id']}</code>\n\n"
        )
        
    await update.message.reply_text(text, parse_mode="HTML")


async def untrack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ <b>Usage:</b> `/untrack <sneaker_id>`", parse_mode="HTML")
        return
        
    sneaker_id = args[0]
    status, result = await make_delete_request(f"/api/sneakers/{sneaker_id}")
    
    if status == 200:
        msg = f"✅ Stopped tracking sneaker <code>{sneaker_id}</code>."
    else:
        msg = f"❌ Could not stop tracking. Sneaker ID <code>{sneaker_id}</code> might not exist."
        
    await update.message.reply_text(msg, parse_mode="HTML")


async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status, sneakers = await make_get_request("/api/sneakers")
    
    if status != 200 or not sneakers:
        await update.message.reply_text("❌ Watchlist is empty or backend is unreachable.")
        return
        
    await update.message.reply_text("🔄 Initiating manual scrape cycle. Updates will post on dashboard shortly...")
    
    async with httpx.AsyncClient() as client:
        for s in sneakers:
            try:
                await client.post(f"{BACKEND_URL}/api/sneakers/{s['id']}/check", timeout=5.0)
            except Exception:
                continue


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "ℹ️ <b>SoleSentry Pro Bot Guide</b>\n\n"
        "This bot delivers real-time notifications for tracked sneakers.\n\n"
        "<b>Available Commands:</b>\n"
        "📝 `/track <url> <target_price> [size]` - Track a new sneaker (e.g. Nike, StockX)\n"
        "📋 `/watchlist` - View your watchlist with active prices\n"
        "❌ `/untrack <sneaker_id>` - Remove a sneaker from watchlist\n"
        "🔄 `/refresh` - Force immediate price checks\n"
        "ℹ️ `/help` - View this help documentation"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


def main():
    if TELEGRAM_BOT_TOKEN == "TELEGRAM_BOT_TOKEN_PLACEHOLDER":
        logger.warning("Telegram Bot Token not configured. Telegram bot service will not start.")
        return
        
    logger.info("Initializing Telegram Bot...")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("track", track_command))
    application.add_handler(CommandHandler("watchlist", watchlist_command))
    application.add_handler(CommandHandler("untrack", untrack_command))
    application.add_handler(CommandHandler("refresh", refresh_command))
    application.add_handler(CommandHandler("help", help_command))
    
    logger.info("Starting Telegram Bot long-polling...")
    application.run_polling()

if __name__ == "__main__":
    main()

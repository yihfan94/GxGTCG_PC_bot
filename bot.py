"""
TCG Price Bot – Pokémon & One Piece
Supports: PriceCharting + eBay sold + SNKRDUNK
Shows card photo for visual confirmation

Also starts a tiny HTTP health server so Render Free
can be kept awake by an uptime monitor.
"""

import logging
import os
import sys
import asyncio
from pathlib import Path
from aiohttp import web

# ---- Force correct import path (Render fix) ----
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Debug: show what files Render actually has
print("=== DEBUG: files in project root ===")
for item in sorted(ROOT.iterdir()):
    print(" ", item.name, "(dir)" if item.is_dir() else "")
print("===================================")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode

from config import TELEGRAM_BOT_TOKEN
from providers import PriceChartingProvider, EbayProvider, SnkrdunkProvider
from utils.search import normalize_query

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Providers
pc = PriceChartingProvider()
ebay = EbayProvider()
snkr = SnkrdunkProvider()


# ---------- Telegram handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *TCG Price Bot*\n\n"
        "I check prices for *Pokémon* and *One Piece* cards from:\n"
        "• PriceCharting (EN + JP raw)\n"
        "• eBay last sold (by condition + avg of last 10)\n"
        "• SNKRDUNK (Grades A / B / C / D)\n\n"
        "Just send a card name, for example:\n"
        "`Charizard 151`\n"
        "`Luffy OP01-003`\n"
        "`Pikachu`\n\n"
        "Or use /pc <card name>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "*Commands*\n"
        "/pcstart – Welcome message\n"
        "/pc <name> – Search a card\n"
        "/pchelp – This message\n\n"
        "You can also just type the card name without any command."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def search_cards(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    """Core search logic – shows multiple results with photos when ambiguous."""
    query = normalize_query(query)
    if not query:
        await update.message.reply_text("Please type a card name.")
        return

    await update.message.reply_chat_action("typing")

    results = await pc.search(query, limit=6)

    if not results:
        await update.message.reply_text(
            f"No results found for *{query}*", parse_mode=ParseMode.MARKDOWN
        )
        return

    # Only one result → go straight to full price view
    if len(results) == 1:
        await send_full_price(update, context, results[0])
        return

    # Multiple results → show selection with photos
    await update.message.reply_text(
        f"Found *{len(results)}* matches for *{query}*.\n"
        "Please choose the correct card:",
        parse_mode=ParseMode.MARKDOWN,
    )

    for card in results:
        caption = (
            f"*{card.name}*\n"
            f"{card.set_name}  {card.number}\n"
            f"Game: {card.game.title()} | Lang: {card.language}"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Select this card", callback_data=f"select:{card.id}")]]
        )

        context.bot_data[card.id] = card

        try:
            if card.image_url:
                await update.message.reply_photo(
                    photo=card.image_url,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard,
                )
            else:
                await update.message.reply_text(
                    caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard,
                )
        except Exception as e:
            logger.warning(f"Could not send photo for {card.name}: {e}")
            await update.message.reply_text(
                caption + "\n(image unavailable)",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
            )


async def send_full_price(update: Update, context: ContextTypes.DEFAULT_TYPE, card):
    """Fetch prices from all sources and send photo + caption."""
    card = await ebay.get_prices(card)
    card = await snkr.get_prices(card)
    card = await pc.get_prices(card)

    caption_parts = [
        f"*{card.name}*",
        f"{card.set_name}  •  {card.number}",
        f"Game: {card.game.title()} | Language: {card.language}",
        "",
        pc.format_prices(card),
        "",
        ebay.format_prices(card),
        "",
        snkr.format_prices(card),
    ]
    caption = "\n".join(caption_parts)

    if len(caption) > 1000:
        caption = caption[:997] + "..."

    chat_id = update.effective_chat.id

    try:
        if card.image_url:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=card.image_url,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode=ParseMode.MARKDOWN,
            )
    except Exception as e:
        logger.error(f"Failed to send price message: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=caption + "\n\n(Could not load card image)",
            parse_mode=ParseMode.MARKDOWN,
        )


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text(
            "Usage: /pc <card name>\nExample: /pc Charizard 151"
        )
        return
    await search_cards(update, context, query)


async def text_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith("/"):
        return
    await search_cards(update, context, update.message.text)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("select:"):
        card_id = data.split(":", 1)[1]
        card = context.bot_data.get(card_id)
        if not card:
            await query.edit_message_caption(
                caption="Card data expired. Please search again."
            )
            return

        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        await send_full_price(update, context, card)


# ---------- Health check server (keeps Render Free awake) ----------

async def health(request):
    return web.Response(text="TCG Price Bot is running ✅")


async def start_health_server():
    """Small HTTP server that Render and uptime monitors can ping."""
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health server started on port {port}")


# ---------- Main ----------

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("pcstart", start))
    application.add_handler(CommandHandler("pchelp", help_cmd))
    application.add_handler(CommandHandler("pc", price_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_search)
    )

    # Start health server + Telegram polling together
    async def post_init(app: Application):
        await start_health_server()

    application.post_init = post_init

    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

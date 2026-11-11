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

# Support both normal folder structure and flattened upload (current Render situation)
try:
    from providers import PriceChartingProvider, EbayProvider, SnkrdunkProvider
    from utils.search import normalize_query
except ModuleNotFoundError:
    # Files were uploaded flat (no providers/ or utils/ folders)
    from pricecharting import PriceChartingProvider
    from ebay import EbayProvider
    from snkrdunk import SnkrdunkProvider
    from search import normalize_query
import library

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Optional: restrict bot to one topic (message_thread_id)
ALLOWED_THREAD_ID = os.getenv("ALLOWED_THREAD_ID", "").strip()

def is_allowed_topic(update: Update) -> bool:
    """Return True if the message is in the allowed topic (or restriction is off)."""
    global ALLOWED_THREAD_ID
    # Prefer saved file if present
    topic_file = Path(__file__).resolve().parent / "allowed_topic.txt"
    if topic_file.exists():
        ALLOWED_THREAD_ID = topic_file.read_text().strip()

    if not ALLOWED_THREAD_ID:
        return True
    thread_id = getattr(update.effective_message, "message_thread_id", None)
    return str(thread_id) == ALLOWED_THREAD_ID

async def debug_thread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply with the current topic's thread ID."""
    thread_id = getattr(update.effective_message, "message_thread_id", None)
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"Thread ID: `{thread_id}`\n"
        f"Chat ID: `{chat_id}`\n\n"
        "Or use /pcsettopic inside the topic to lock the bot to it.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def set_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lock the bot to the current topic (same style as other project)."""
    thread_id = getattr(update.effective_message, "message_thread_id", None)
    if not thread_id:
        await update.message.reply_text(
            "This chat has no topics. Send /pcsettopic inside a topic."
        )
        return

    # Save to a small local file so it survives restarts
    topic_file = Path(__file__).resolve().parent / "allowed_topic.txt"
    topic_file.write_text(str(thread_id))

    # Also update the in-memory value
    global ALLOWED_THREAD_ID
    ALLOWED_THREAD_ID = str(thread_id)

    await update.message.reply_text(
        f"Bot is now restricted to this topic (Thread ID: `{thread_id}`).\n"
        "It will ignore messages from other topics.",
        parse_mode=ParseMode.MARKDOWN,
    )


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
        "Or use /pc <card name>\n\nYou can also send a photo of the card.\n\nLibrary: /pclibrary"
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
    if not is_allowed_topic(update):
        return
    query = normalize_query(query)
    if not query:
        await update.message.reply_text("Please type a card name.")
        return

    await update.message.reply_chat_action("typing")

    results = await pc.search(query, limit=4)

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
        # Escape markdown special chars to avoid parse errors
        safe_name = card.name.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[")
        safe_set = (card.set_name or "").replace("_", "\\_").replace("*", "\\*")
        caption = (
            f"*{safe_name}*\n"
            f"{safe_set}  {card.number}\n"
            f"Game: {card.game.title()} | Lang: {card.language}"
        )
        if not card.image_url:
            caption += "\n(image unavailable)"
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
    try:
        card = await ebay.get_prices(card)
    except Exception:
        pass
    try:
        card = await snkr.get_prices(card)
    except Exception:
        pass
    try:
        card = await pc.get_prices(card)
    except Exception:
        pass

    # Escape markdown
    safe_name = (card.name or "").replace("_", "\\_").replace("*", "\\*").replace("[", "\\[")
    safe_set = (card.set_name or "").replace("_", "\\_").replace("*", "\\*")

    caption_parts = [
        f"*{safe_name}*",
        f"{safe_set}  •  {card.number}",
        f"Game: {card.game.title()} | Language: {card.language}",
        "",
        pc.format_prices(card) or "PriceCharting: not found",
        "",
        ebay.format_prices(card) or "eBay: not found",
        "",
        snkr.format_prices(card) or "SNKRDUNK: not found",
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
    if not is_allowed_topic(update):
        return
    if update.message.text.startswith("/"):
        return

    awaiting = context.user_data.get("awaiting")
    text = update.message.text.strip()

    if awaiting == "add_name":
        context.user_data["pending_name"] = text
        context.user_data["awaiting"] = "add_price"
        await update.message.reply_text("Bought price (e.g. 45.00):")
        return

    if awaiting == "add_price":
        try:
            price = float(text)
        except ValueError:
            await update.message.reply_text("Please enter a valid number.")
            return
        name = context.user_data.get("pending_name", "Unknown")
        card_id = library.add_card(name=name, bought_price=price)
        context.user_data.pop("awaiting", None)
        context.user_data.pop("pending_name", None)
        await update.message.reply_text(
            f"Added '{name}' to Not in binder at ${price:.2f}.\nID: {card_id}"
        )
        return

    if awaiting == "sold_id":
        context.user_data["pending_sold_id"] = text
        context.user_data["awaiting"] = "sold_price"
        await update.message.reply_text("Sold price:")
        return

    if awaiting == "sold_price":
        try:
            sold_price = float(text)
        except ValueError:
            await update.message.reply_text("Please enter a valid number.")
            return
        card_id = context.user_data.get("pending_sold_id")
        if library.mark_sold(card_id, sold_price):
            await update.message.reply_text(f"Marked {card_id} as sold at ${sold_price:.2f}.")
        else:
            await update.message.reply_text("Card not found.")
        context.user_data.pop("awaiting", None)
        context.user_data.pop("pending_sold_id", None)
        return

    # Normal card search
    await search_cards(update, context, text)


async def photo_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages for card identification."""
    if not is_allowed_topic(update):
        return
    photo = update.message.photo[-1]  # highest resolution
    file = await context.bot.get_file(photo.file_id)

    # Store file_id so we can re-send the user's photo later if needed
    context.user_data["last_photo_file_id"] = photo.file_id

    await update.message.reply_text(
        "📷 Photo received!\n\n"
        "I can search by name right now.\n"
        "Please type the card name (e.g. `Charizard 151` or `Luffy OP01`) "
        "and I will show matching cards with prices.\n\n"
        "_Full automatic photo identification is coming — for now text search is the most accurate._",
        parse_mode=ParseMode.MARKDOWN,
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # Price search selection
    if data.startswith("select:"):
        card_id = data.split(":", 1)[1]
        card = context.bot_data.get(card_id)
        if not card:
            try:
                await query.edit_message_text("Card data expired. Please search again.")
            except Exception:
                await query.message.reply_text("Card data expired. Please search again.")
            return
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        try:
            await send_full_price(update, context, card)
        except Exception as e:
            await query.message.reply_text(f"Could not load prices: {e}")
        return

    # Library menu actions
    if data == "lib:add":
        context.user_data["awaiting"] = "add_name"
        await query.edit_message_text("Type the card name (e.g. Charizard 151):")
        return

    if data == "lib:binders":
        binders = library.get_binders()
        await query.edit_message_text("Binders:\n" + "\n".join(f"• {b}" for b in binders))
        return

    if data == "lib:summary":
        cards = library.get_cards()
        spent = sum(c["bought_price"] * c["quantity"] for c in cards)
        sold = sum((c["sold_price"] or 0) * c["quantity"] for c in cards if c["sold_price"])
        profit = sold - spent
        margin = (profit / spent * 100) if spent else 0
        text = (
            f"*Library Summary*\n"
            f"Total spent: ${spent:.2f}\n"
            f"Total sold: ${sold:.2f}\n"
            f"Total profit: ${profit:.2f}\n"
            f"Margin: {margin:.1f}%"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        return

    if data == "lib:sold":
        context.user_data["awaiting"] = "sold_id"
        await query.edit_message_text("Type the card ID to mark as sold:")
        return

    if data == "lib:backup":
        path = library.export_library()
        await query.message.reply_document(
            document=open(path, "rb"),
            filename="library_backup.json",
            caption="Your library backup."
        )
        await query.edit_message_text("Backup sent.")
        return


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

async def library_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main library menu with buttons."""
    if not is_allowed_topic(update):
        return
    keyboard = [
        [InlineKeyboardButton("Add card", callback_data="lib:add")],
        [InlineKeyboardButton("View binders", callback_data="lib:binders")],
        [InlineKeyboardButton("Summary", callback_data="lib:summary")],
        [InlineKeyboardButton("Mark sold", callback_data="lib:sold")],
        [InlineKeyboardButton("Backup", callback_data="lib:backup")],
    ]
    await update.message.reply_text(
        "*Library Menu*\nChoose an action:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
    )


async def binder_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    binders = library.get_binders()
    await update.message.reply_text("Binders:\n" + "\n".join(f"• {b}" for b in binders))


async def binder_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /pcbinder create <name>")
        return
    name = " ".join(context.args)
    if library.add_binder(name):
        await update.message.reply_text(f"Binder '{name}' created.")
    else:
        await update.message.reply_text("Binder already exists or is reserved.")


async def library_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /pcadd <card name> <bought price>\n"
            "Example: /pcadd Charizard 151 45.00"
        )
        return
    try:
        price = float(context.args[-1])
        name = " ".join(context.args[:-1])
    except ValueError:
        await update.message.reply_text("Bought price must be a number.")
        return
    card_id = library.add_card(name=name, bought_price=price)
    await update.message.reply_text(
        f"Added '{name}' to Not in binder at ${price:.2f}.\nID: {card_id}"
    )


async def library_sold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /pcsold <card_id> <sold price>")
        return
    card_id = context.args[0]
    try:
        sold_price = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Sold price must be a number.")
        return
    if library.mark_sold(card_id, sold_price):
        await update.message.reply_text(f"Marked {card_id} as sold at ${sold_price:.2f}.")
    else:
        await update.message.reply_text("Card not found.")


async def library_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cards = library.get_cards()
    spent = sum(c["bought_price"] * c["quantity"] for c in cards)
    sold = sum((c["sold_price"] or 0) * c["quantity"] for c in cards if c["sold_price"])
    profit = sold - spent
    margin = (profit / spent * 100) if spent else 0
    text = (
        f"*Library Summary*\n"
        f"Total spent: ${spent:.2f}\n"
        f"Total sold: ${sold:.2f}\n"
        f"Total profit: ${profit:.2f}\n"
        f"Margin: {margin:.1f}%"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def tradeshow_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /pctradeshow add <name> <YYYY-MM-DD> <YYYY-MM-DD>"
        )
        return
    name = context.args[0]
    start, end = context.args[1], context.args[2]
    if library.add_tradeshow(name, start, end):
        await update.message.reply_text(f"Tradeshow '{name}' saved ({start} to {end}).")
    else:
        await update.message.reply_text("Tradeshow name already exists.")


async def backup_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = library.export_library()
    await update.message.reply_document(
        document=open(path, "rb"),
        filename="library_backup.json",
        caption="Your library backup. Keep this file safe."
    )


def main():
    # Fix for Python 3.10+ / 3.12+ / 3.14 on Render (no default event loop)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("pcstart", start))
    application.add_handler(CommandHandler("pcdebug", debug_thread))
    application.add_handler(CommandHandler("pcsettopic", set_topic))
    application.add_handler(CommandHandler("pchelp", help_cmd))
    application.add_handler(CommandHandler("pc", price_command))
    application.add_handler(CommandHandler("pclibrary", library_menu))
    application.add_handler(CommandHandler("pcbinder", binder_list))
    application.add_handler(CommandHandler("pcbindercreate", binder_create))
    application.add_handler(CommandHandler("pcadd", library_add))
    application.add_handler(CommandHandler("pcsold", library_sold))
    application.add_handler(CommandHandler("pcsummary", library_summary))
    application.add_handler(CommandHandler("pctradeshow", tradeshow_add))
    application.add_handler(CommandHandler("pcbackup", backup_export))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_search)
    )
    application.add_handler(
        MessageHandler(filters.PHOTO, photo_search)
    )

    # Start health server + Telegram polling together
    async def post_init(app: Application):
        await start_health_server()

    application.post_init = post_init

    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

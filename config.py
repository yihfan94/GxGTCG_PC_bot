import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError(
        "TELEGRAM_BOT_TOKEN is missing. "
        "Create a .env file from .env.example and add your token from @BotFather."
    )

# Optional keys (leave empty for now – placeholders will be used)
PRICECHARTING_API_KEY = os.getenv("PRICECHARTING_API_KEY", "")
EBAY_SOLD_API_KEY = os.getenv("EBAY_SOLD_API_KEY", "")
SNKRDUNK_API_KEY = os.getenv("SNKRDUNK_API_KEY", "")
REEFAPI_KEY = os.getenv("REEFAPI_KEY", "")
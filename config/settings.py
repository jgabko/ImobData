# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

# ── Scraping ──────────────────────────────────────────────
TARGET_CITY = os.getenv("TARGET_CITY", "curitiba")
TARGET_STATE = os.getenv("TARGET_STATE", "pr")
MAX_PAGES = int(os.getenv("MAX_PAGES", "5"))
REQUEST_DELAY_SECONDS = float(os.getenv("REQUEST_DELAY_SECONDS", "2.5"))

# ── Paths ─────────────────────────────────────────────────
DATA_LAKE_PATH = os.getenv("DATA_LAKE_PATH", "data/raw")
DATA_WAREHOUSE_PATH = os.getenv("DATA_WAREHOUSE_PATH", "data/processed")

# ── Database ──────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "real_estate")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# ── Telegram ──────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Análise ───────────────────────────────────────────────
ARBITRAGE_THRESHOLD = float(os.getenv("ARBITRAGE_THRESHOLD", "0.20"))
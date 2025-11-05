import os
from dotenv import load_dotenv

# Load dari .env file
load_dotenv()

# ========================
# Telegram Bot
# ========================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "defaultsecret123")

# Base URL backend (untuk webhook public)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://kodex-backendapi2.up.railway.app")

# ========================
# Binance & Market
# ========================
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")

# ========================
# Database
# ========================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kodex_registry.db")

# ========================
# System Mode
# ========================
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

"""Configuration management"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STATE_FILE = DATA_DIR / "state.json"

# Telegram settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Search settings
SEARCH_QUERIES = os.getenv("SEARCH_QUERIES", "presale").split(",")
SEARCH_QUERIES = [q.strip() for q in SEARCH_QUERIES]

# Provider settings
ENABLE_VK = os.getenv("ENABLE_VK", "true").lower() == "true"
ENABLE_YANDEX = os.getenv("ENABLE_YANDEX", "true").lower() == "true"

# HTTP settings
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))
USER_AGENT = os.getenv("USER_AGENT", "VacancyWatcher/1.0 (https://github.com/job-hunter)")

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

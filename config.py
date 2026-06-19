import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment")

CARD_NUMBER = "8800406260285884"
CARD_OWNER = "Husanboy"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.getenv("DATABASE") or os.path.join(DATA_DIR, "stars_shop.db")

PACKAGES = [
    {"key": "50", "title": "⭐ 50 Stars", "count": 50, "price": 11500},
    {"key": "100", "title": "⭐ 100 Stars", "count": 100, "price": 23000},
    {"key": "250", "title": "⭐ 250 Stars", "count": 250, "price": 57500},
    {"key": "500", "title": "⭐ 500 Stars", "count": 500, "price": 115000},
    {"key": "1000", "title": "⭐ 1000 Stars", "count": 1000, "price": 230000},
]

LOG_DIR = os.path.join(BASE_DIR, "logs")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
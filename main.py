import logging
import sys
import time
from config import BOT_TOKEN, LOG_DIR, DATA_DIR, BACKUP_DIR, IMAGES_DIR, ADMIN_ID
from utils import ensure_dirs, install_requirements
from flask import Flask
import threading
from database import Database
from keyboards import Keyboards
from handlers import register_handlers
import telebot


def setup_logging():
    ensure_dirs(LOG_DIR)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(f"{LOG_DIR}/bot.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    # optionally install requirements (kept for local use)
    print("Checking and installing requirements (if needed)...")
    ok, out = install_requirements("requirements.txt")
    if not ok:
        print("Failed to install requirements:\n", out)
    else:
        print(out)

    setup_logging()
    ensure_dirs(DATA_DIR, IMAGES_DIR, BACKUP_DIR, LOG_DIR)

    logging.info("Starting StarsShop bot")

    db = Database()
    kb = Keyboards()

    # ensure admin id from environment is stored in DB settings
    try:
        if ADMIN_ID:
            db.set_setting('admin_id', str(ADMIN_ID))
            logging.info("Admin ID set from environment: %s", ADMIN_ID)
    except Exception:
        logging.exception("Failed to set ADMIN_ID from environment")

    # start a minimal web server for Render health checks
    app = Flask(__name__)

    @app.route('/')
    def index():
        return 'OK'

    def run_web():
        import os
        port = int(os.getenv('PORT', '5000'))
        app.run(host='0.0.0.0', port=port)

    t = threading.Thread(target=run_web, daemon=True)
    t.start()

    try:
        bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
    except Exception as e:
        logging.exception("Failed to create bot instance: %s", e)
        raise

    register_handlers(bot, db, kb)

    logging.info("Database connected")
    print("Bot started successfully")
    print("Database connected")
    print("Waiting for users...")

    # resilient polling loop
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=5)
        except Exception as e:
            logging.exception("Polling crashed: %s", e)
            time.sleep(5)


if __name__ == "__main__":
    main()

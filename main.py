import logging
import sys
import time
import os
import threading
from flask import Flask

import telebot

from config import BOT_TOKEN, LOG_DIR, DATA_DIR, BACKUP_DIR, IMAGES_DIR, ADMIN_ID
from utils import ensure_dirs
from database import Database
from keyboards import Keyboards
from handlers import register_handlers


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


def run_web():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return "OK"

    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


def main():
    print("Starting bot...")

    setup_logging()

    ensure_dirs(DATA_DIR, IMAGES_DIR, BACKUP_DIR, LOG_DIR)

    logging.info("Bot is starting")

    db = Database()
    kb = Keyboards()

    # admin id save
    try:
        if ADMIN_ID:
            db.set_setting("admin_id", str(ADMIN_ID))
    except Exception:
        logging.exception("Admin ID error")

    # start flask (Render health check)
    threading.Thread(target=run_web, daemon=True).start()

    # bot init
    try:
        bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
    except Exception as e:
        logging.exception("Bot init error: %s", e)
        return

    register_handlers(bot, db, kb)

    print("Bot started ✔")
    logging.info("Bot started successfully")

    # polling loop (stable)
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=10)
        except Exception as e:
            logging.exception("Polling crashed: %s", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
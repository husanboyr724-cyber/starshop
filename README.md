# StarsShop Telegram Bot

This project provides a production-ready Telegram bot for selling Telegram Stars. It uses Python 3, pyTelegramBotAPI, and SQLite.

Features:
- Beautiful inline UI
- Payment instructions and receipt handling
- Admin panel with statistics, broadcast and order management
- SQLite database with automatic schema creation
- Logging and backups
- Rate-limiting and error handling

Run:

1. Edit `.env` and set `BOT_TOKEN`.
2. (Optional) adjust packages in `config.py`.
3. Install requirements and start the bot:

```bash
pip install -r requirements.txt
python main.py
```

The bot will create the database at `data/stars_shop.db` and create `logs/`, `images/`, `backups/` automatically.

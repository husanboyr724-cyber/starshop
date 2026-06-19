import sqlite3
import threading
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
from config import DB_PATH, PACKAGES
from utils import ensure_dirs


class Database:
    def __init__(self, path: str = None):
        self.path = path or DB_PATH
        ensure_dirs(os.path.dirname(self.path))
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _execute(self, sql: str, params: tuple = ()):
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            self._conn.commit()
            return cur

    def _ensure_schema(self):
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                full_name TEXT,
                registered_at TEXT,
                banned INTEGER DEFAULT 0
            )
            """
            )

            cur.execute(
                """
            CREATE TABLE IF NOT EXISTS prices (
                key TEXT PRIMARY KEY,
                title TEXT,
                count INTEGER,
                price INTEGER
            )
            """
            )

            cur.execute(
                """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                username TEXT,
                full_name TEXT,
                package_key TEXT,
                package_title TEXT,
                package_count INTEGER,
                price INTEGER,
                receipt_file_id TEXT,
                status TEXT,
                created_at TEXT
            )
            """
            )

            cur.execute(
                """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
            )

            cur.execute(
                """
            CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT,
                created_at TEXT,
                recipients INTEGER
            )
            """
            )

            cur.execute(
                """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                message TEXT,
                created_at TEXT
            )
            """
            )

            self._conn.commit()

        # ensure default prices
        for p in PACKAGES:
            if not self.get_price(p["key"]):
                self.add_price(p["key"], p["title"], p["count"], p["price"]) 

    # Settings
    def set_setting(self, key: str, value: str):
        self._execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key, value))

    def get_setting(self, key: str) -> Optional[str]:
        cur = self._execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else None

    # Users
    def add_or_update_user(self, telegram_id: int, username: Optional[str], full_name: Optional[str]):
        now = datetime.utcnow().isoformat()
        cur = self._execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        if cur.fetchone():
            self._execute("UPDATE users SET username = ?, full_name = ? WHERE telegram_id = ?", (username, full_name, telegram_id))
        else:
            self._execute("INSERT INTO users (telegram_id,username,full_name,registered_at) VALUES (?,?,?,?)", (telegram_id, username, full_name, now))

    def ban_user(self, telegram_id: int):
        self._execute("UPDATE users SET banned = 1 WHERE telegram_id = ?", (telegram_id,))

    def unban_user(self, telegram_id: int):
        self._execute("UPDATE users SET banned = 0 WHERE telegram_id = ?", (telegram_id,))

    def is_banned(self, telegram_id: int) -> bool:
        cur = self._execute("SELECT banned FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        return bool(row[0]) if row else False

    def list_users(self) -> List[sqlite3.Row]:
        cur = self._execute("SELECT * FROM users ORDER BY registered_at DESC")
        return cur.fetchall()

    # Prices
    def add_price(self, key: str, title: str, count: int, price: int):
        self._execute("INSERT OR REPLACE INTO prices (key,title,count,price) VALUES (?,?,?,?)", (key, title, count, price))

    def get_price(self, key: str) -> Optional[sqlite3.Row]:
        cur = self._execute("SELECT * FROM prices WHERE key = ?", (key,))
        return cur.fetchone()

    def get_all_prices(self) -> List[sqlite3.Row]:
        cur = self._execute("SELECT * FROM prices ORDER BY CAST(key AS INTEGER)")
        return cur.fetchall()

    def update_price(self, key: str, price: int):
        self._execute("UPDATE prices SET price = ? WHERE key = ?", (price, key))

    # Orders
    def create_order(self, telegram_id: int, username: str, full_name: str, price_item: sqlite3.Row) -> int:
        now = datetime.utcnow().isoformat()
        cur = self._execute(
            "INSERT INTO orders (telegram_id,username,full_name,package_key,package_title,package_count,price,status,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (telegram_id, username, full_name, price_item["key"], price_item["title"], price_item["count"], price_item["price"], "awaiting_receipt", now),
        )
        return cur.lastrowid

    def attach_receipt(self, order_id: int, file_id: str):
        self._execute("UPDATE orders SET receipt_file_id = ?, status = ? WHERE id = ?", (file_id, "pending", order_id))

    def update_order_status(self, order_id: int, status: str):
        self._execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))

    def get_order(self, order_id: int) -> Optional[sqlite3.Row]:
        cur = self._execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        return cur.fetchone()

    def list_orders(self, status: Optional[str] = None) -> List[sqlite3.Row]:
        if status:
            cur = self._execute("SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC", (status,))
        else:
            cur = self._execute("SELECT * FROM orders ORDER BY created_at DESC")
        return cur.fetchall()

    def get_latest_awaiting_order(self, telegram_id: int) -> Optional[sqlite3.Row]:
        cur = self._execute("SELECT * FROM orders WHERE telegram_id = ? AND (status = 'awaiting_receipt' OR status = 'pending') ORDER BY id DESC LIMIT 1", (telegram_id,))
        return cur.fetchone()

    # Broadcasts
    def add_broadcast(self, message: str, recipients: int):
        now = datetime.utcnow().isoformat()
        self._execute("INSERT INTO broadcasts (message,created_at,recipients) VALUES (?,?,?)", (message, now, recipients))

    # Logs
    def add_log(self, level: str, message: str):
        now = datetime.utcnow().isoformat()
        self._execute("INSERT INTO logs (level,message,created_at) VALUES (?,?,?)", (level, message, now))

    # Export and backup
    def export_db(self, dst_path: str) -> bool:
        try:
            ensure_dirs(os.path.dirname(dst_path))
            with open(self.path, "rb") as src, open(dst_path, "wb") as dst:
                dst.write(src.read())
            return True
        except Exception:
            return False

-- SQLite schema for Stars Market orders
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL,
  stars_package INTEGER NOT NULL,
  amount INTEGER NOT NULL,
  screenshot TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);

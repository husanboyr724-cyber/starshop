import os
import sys
import logging
import subprocess
import threading
import time
from functools import wraps
from typing import Callable, Any
from pathlib import Path
import traceback


def ensure_dirs(*paths):
    for p in paths:
        try:
            os.makedirs(p, exist_ok=True)
        except Exception:
            pass


def install_requirements(requirements_file: str):
    try:
        if not os.path.exists(requirements_file):
            return True, "requirements file not found"
        cmd = [sys.executable, "-m", "pip", "install", "-r", requirements_file]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return False, proc.stderr
        return True, proc.stdout
    except Exception as e:
        return False, str(e)


class RateLimiter:
    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self._last = {}
        self._lock = threading.Lock()

    def allowed(self, key: Any) -> bool:
        with self._lock:
            now = time.time()
            last = self._last.get(key, 0)
            if now - last < self.interval:
                return False
            self._last[key] = now
            return True


rate_limiter = RateLimiter(interval=0.5)


def safe_handler(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            # Log full exception and print traceback to console for visibility
            logging.exception("Unhandled exception in handler %s", func.__name__)
            traceback.print_exc()
    return wrapper


def format_currency(amount: int) -> str:
    try:
        return f"{amount:,} UZS"
    except Exception:
        return f"{amount} UZS"


def now_iso():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


def backup_file(src: str, dst_dir: str):
    try:
        ensure_dirs(dst_dir)
        p = Path(src)
        ts = int(time.time())
        dst = Path(dst_dir) / f"backup_{p.stem}_{ts}{p.suffix}"
        with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
            fdst.write(fsrc.read())
        return True, str(dst)
    except Exception as e:
        return False, str(e)

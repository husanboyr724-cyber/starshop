import os
import sqlite3
import datetime
import time
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_from_directory, abort
import requests

# Configuration
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / 'uploads'
DB_PATH = BASE_DIR / 'orders.db'
ALLOWED_EXT = {'png', 'jpg', 'jpeg'}

# Telegram bot config - set BOT_TOKEN in environment for real sending
BOT_TOKEN = os.environ.get("8983851121:AAF5xEWTgf204EsrFk1bZoLKnxdsQPHCkhY" )
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '8292923975')

if not UPLOAD_FOLDER.exists():
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)


def get_db_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    schema = '''
    CREATE TABLE IF NOT EXISTS orders (
      id TEXT PRIMARY KEY,
      username TEXT NOT NULL,
      stars_package INTEGER NOT NULL,
      amount INTEGER NOT NULL,
      screenshot TEXT,
      status TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
    '''
    with get_db_conn() as conn:
        conn.executescript(schema)
        conn.commit()


def allowed_file(filename):
    if not filename: return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def send_telegram_message(text):
    if not BOT_TOKEN:
        app.logger.warning('BOT_TOKEN not set; skipping telegram sendMessage')
        return False
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    try:
        r = requests.post(url, data={'chat_id': ADMIN_CHAT_ID, 'text': text})
        r.raise_for_status()
        return True
    except Exception as e:
        app.logger.exception('Failed to send telegram message: %s', e)
        return False


def send_telegram_photo(photo_path, caption=''):
    if not BOT_TOKEN:
        app.logger.warning('BOT_TOKEN not set; skipping telegram sendPhoto')
        return False
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto'
    try:
        with open(photo_path, 'rb') as f:
            files = {'photo': f}
            data = {'chat_id': ADMIN_CHAT_ID, 'caption': caption}
            r = requests.post(url, data=data, files=files)
            r.raise_for_status()
            return True
    except Exception as e:
        app.logger.exception('Failed to send telegram photo: %s', e)
        return False


@app.route('/create-order', methods=['POST'])
@app.route('/api/orders', methods=['POST'])
def create_order():
    """Accept multipart/form-data with fields: id (optional), user, pkg, price/amount, method, screenshot(file)"""
    # form fields
    order_id = request.form.get('id') or request.form.get('order_id')
    username = request.form.get('user') or request.form.get('username')
    pkg = request.form.get('pkg') or request.form.get('stars_package')
    price = request.form.get('price') or request.form.get('amount')
    method = request.form.get('method') or request.form.get('pay_method')

    if not username or not pkg or not price:
        return jsonify({'ok': False, 'error': 'Missing required fields (user, pkg, price)'}), 400

    # ensure order id
    if not order_id:
        order_id = 'o' + str(int(time.time() * 1000))

    # file
    file = request.files.get('screenshot') or request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'ok': False, 'error': 'Screenshot file is required'}), 400
    if not allowed_file(file.filename):
        return jsonify({'ok': False, 'error': 'Invalid file type'}), 400

    filename = secure_filename(f"{order_id}_{int(time.time())}.{file.filename.rsplit('.',1)[1].lower()}")
    saved_path = UPLOAD_FOLDER / filename
    file.save(str(saved_path))

    created_at = datetime.datetime.utcnow().isoformat()
    status = 'Pending'

    # save to DB
    with get_db_conn() as conn:
        conn.execute('INSERT OR REPLACE INTO orders (id, username, stars_package, amount, screenshot, status, created_at) VALUES (?,?,?,?,?,?,?)',
                     (order_id, username, int(pkg), int(price), filename, status, created_at))
        conn.commit()

    # notify admin via telegram
    text = f"New Order\nUsername: {username}\nStars: {pkg}\nAmount: {price} UZS\nOrder ID: {order_id}"
    send_telegram_message(text)
    # send photo
    try:
        send_telegram_photo(str(saved_path), caption=text)
    except Exception:
        app.logger.exception('Photo send failed')

    return jsonify({'ok': True, 'order_id': order_id})


@app.route('/orders', methods=['GET'])
def list_orders():
    conn = get_db_conn()
    cur = conn.execute('SELECT id, username, stars_package, amount, screenshot, status, created_at FROM orders ORDER BY created_at DESC')
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({'ok': True, 'orders': rows})


def update_order_status(order_id, new_status):
    with get_db_conn() as conn:
        cur = conn.execute('SELECT * FROM orders WHERE id=?', (order_id,))
        r = cur.fetchone()
        if not r:
            return None
        conn.execute('UPDATE orders SET status=? WHERE id=?', (new_status, order_id))
        conn.commit()
        return dict(r)


@app.route('/approve-order', methods=['POST'])
def approve_order():
    data = request.get_json() or request.form
    order_id = data.get('id')
    if not order_id:
        return jsonify({'ok': False, 'error': 'Missing id'}), 400
    prev = update_order_status(order_id, 'Approved')
    if not prev:
        return jsonify({'ok': False, 'error': 'Order not found'}), 404
    send_telegram_message(f"Order Approved\nID: {order_id}\nUser: {prev['username']}")
    return jsonify({'ok': True})


@app.route('/reject-order', methods=['POST'])
def reject_order():
    data = request.get_json() or request.form
    order_id = data.get('id')
    if not order_id:
        return jsonify({'ok': False, 'error': 'Missing id'}), 400
    prev = update_order_status(order_id, 'Rejected')
    if not prev:
        return jsonify({'ok': False, 'error': 'Order not found'}), 404
    send_telegram_message(f"Order Rejected\nID: {order_id}\nUser: {prev['username']}")
    return jsonify({'ok': True})


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(str(UPLOAD_FOLDER), filename)


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)

import logging
from telebot import types
import telebot
import traceback
from config import BOT_TOKEN, CARD_NUMBER, CARD_OWNER
from database import Database
from keyboards import Keyboards
from utils import rate_limiter, safe_handler, format_currency, now_iso, backup_file
from states import OrderStatus, UserState
import time


def register_handlers(bot: telebot.TeleBot, db: Database, kb: Keyboards):

    @bot.message_handler(commands=["start"])
    @safe_handler
    def cmd_start(message: types.Message):
        user = message.from_user
        if not rate_limiter.allowed(user.id):
            return

        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        db.add_or_update_user(user.id, user.username or '', full_name)

        # auto-detect admin if not set in settings
        admin_setting = db.get_setting('admin_id')
        if not admin_setting:
            db.set_setting('admin_id', str(user.id))
            bot.send_message(user.id, "You have been set as admin for this bot.")

        text = (
            "✨ <b>Welcome to Telegram Stars Shop</b> ✨\n\n"
            "Buy Telegram Stars quickly and securely.\n\n"
            "✅ Fast Delivery\n"
            "✅ Trusted Service\n"
            "✅ 24/7 Support\n\n"
            "Please choose a package below."
        )
        bot.send_message(message.chat.id, text, reply_markup=kb.main_menu())

    @bot.callback_query_handler(func=lambda c: True)
    @safe_handler
    def callback_query(call: types.CallbackQuery):
        data = call.data
        user = call.from_user

        logging.info("Callback query from %s: %s", getattr(user, 'id', None), data)

        admin_id = db.get_setting('admin_id')
        admin_id = int(admin_id) if admin_id else None

        if data == 'back_to_main':
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=(
                "✨ <b>Welcome to Telegram Stars Shop</b> ✨\n\n"
                "Buy Telegram Stars quickly and securely.\n\n"
                "✅ Fast Delivery\n"
                "✅ Trusted Service\n"
                "✅ 24/7 Support\n\n"
                "Please choose a package below."
            ), reply_markup=kb.main_menu())
            bot.answer_callback_query(call.id)
            return

        if data.startswith('package:'):
            key = data.split(':', 1)[1]
            price = db.get_price(key)
            if not price:
                bot.answer_callback_query(call.id, 'Package not found')
                return
            text = (
                f"<b>Selected package</b>\n\n{price['title']} — {format_currency(price['price'])}\n\n"
                f"<b>Card Number:</b> {CARD_NUMBER}\n"
                f"<b>Card Holder:</b> {CARD_OWNER}\n\n"
                "<b>Payment instructions</b>\nPlease transfer the exact amount and then send a screenshot of the payment receipt."
            )
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=kb.package_page(price))
            bot.answer_callback_query(call.id)
            return

        if data.startswith('pay:'):
            key = data.split(':', 1)[1]
            price = db.get_price(key)
            if not price:
                bot.answer_callback_query(call.id, 'Package not found')
                return
            order_id = db.create_order(user.id, user.username or '', f"{user.first_name or ''} {user.last_name or ''}".strip(), price)
            text = (
                f"Please transfer the exact amount to the following card.\n\n"
                f"<b>Card Number:</b> {CARD_NUMBER}\n"
                f"<b>Card Holder:</b> {CARD_OWNER}\n\n"
                f"After payment, send the screenshot of your payment receipt here.\n\nOrder ID: {order_id}"
            )
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=kb.payment_keyboard())
            bot.answer_callback_query(call.id)
            return

        if data == 'send_receipt':
            bot.send_message(call.message.chat.id, 'Please send a photo of your payment receipt now.')
            bot.answer_callback_query(call.id)
            return

        if data == 'my_orders':
            orders = db.list_orders()
            parts = []
            for o in orders:
                if o['telegram_id'] == user.id:
                    parts.append(f"#{o['id']} — {o['package_title']} — {format_currency(o['price'])} — {o['status']}")
            text = 'Your orders:\n' + ('\n'.join(parts) if parts else 'You have no orders yet.')
            bot.send_message(call.message.chat.id, text)
            bot.answer_callback_query(call.id)
            return

        if data == 'contact_admin':
            if admin_id:
                bot.send_message(call.message.chat.id, f"Contact admin: {admin_id}")
            else:
                bot.send_message(call.message.chat.id, "Admin is not set.")
            bot.answer_callback_query(call.id)
            return

        if data == 'help':
            bot.send_message(call.message.chat.id, 'Send /start to view packages. For payment help contact admin.')
            bot.answer_callback_query(call.id)
            return

        if data.startswith('admin:'):
            if user.id != admin_id:
                bot.answer_callback_query(call.id, 'Unauthorized')
                return
            parts = data.split(':')
            action = parts[1] if len(parts) > 1 else ''
            if action == 'stats':
                s = {
                    'total_users': len(db.list_users()),
                    'total_orders': len(db.list_orders()),
                }
                bot.send_message(user.id, f"📊 Statistics\nTotal Users: {s['total_users']}\nTotal Orders: {s['total_orders']}")
                bot.answer_callback_query(call.id)
                return
            if action == 'orders':
                orders = db.list_orders()
                text = '<b>Orders</b>\n\n'
                for o in orders[:200]:
                    text += f"#{o['id']} {o['package_title']} {format_currency(o['price'])} — {o['status']}\n"
                bot.send_message(user.id, text)
                bot.answer_callback_query(call.id)
                return
            if action == 'users':
                users = db.list_users()
                text = f"<b>Users</b> ({len(users)})\n\n"
                for u in users[:200]:
                    text += f"{u['telegram_id']} — {u['username'] or '-'} — {u['full_name'] or '-'}\n"
                bot.send_message(user.id, text)
                bot.answer_callback_query(call.id)
                return

        if data.startswith('admin:approve:') or data.startswith('admin:reject:'):
            if user.id != admin_id:
                bot.answer_callback_query(call.id, 'Unauthorized')
                return
            parts = data.split(':', 2)
            action = parts[1] if len(parts) > 1 else ''
            try:
                order_id = int(parts[2]) if len(parts) > 2 else None
            except Exception:
                logging.exception("Invalid order id in callback: %s", data)
                bot.answer_callback_query(call.id, 'Invalid order id')
                return

            if not order_id:
                bot.answer_callback_query(call.id, 'Order id missing')
                return

            if action == 'approve':
                try:
                    db.update_order_status(order_id, 'completed')
                    order = db.get_order(order_id)
                    if not order:
                        bot.answer_callback_query(call.id, 'Order not found')
                        return
                    # notify user
                    try:
                        bot.send_message(order['telegram_id'], '✅ Payment confirmed!\n\nYour order has been accepted.\nTelegram Stars will be sent shortly.\nThank you!')
                    except Exception:
                        logging.exception("Failed to send approval message to user %s", order['telegram_id'])
                        traceback.print_exc()
                    # remove inline buttons from admin message
                    try:
                        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
                        bot.send_message(user.id, f"Order #{order_id} approved.")
                    except Exception:
                        logging.exception("Failed to update admin message for order %s", order_id)
                        traceback.print_exc()
                    bot.answer_callback_query(call.id, 'Order approved')
                    return
                except Exception:
                    logging.exception("Error while approving order %s", order_id)
                    traceback.print_exc()
                    bot.answer_callback_query(call.id, 'Failed to approve order')
                    return
            else:
                try:
                    db.update_order_status(order_id, 'rejected')
                    order = db.get_order(order_id)
                    if not order:
                        bot.answer_callback_query(call.id, 'Order not found')
                        return
                    try:
                        bot.send_message(order['telegram_id'], '❌ Payment could not be verified.\n\nPlease check your receipt and try again.')
                    except Exception:
                        logging.exception("Failed to send rejection message to user %s", order['telegram_id'])
                        traceback.print_exc()
                    try:
                        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
                        bot.send_message(user.id, f"Order #{order_id} rejected.")
                    except Exception:
                        logging.exception("Failed to update admin message for order %s", order_id)
                        traceback.print_exc()
                    bot.answer_callback_query(call.id, 'Order rejected')
                    return
                except Exception:
                    logging.exception("Error while rejecting order %s", order_id)
                    traceback.print_exc()
                    bot.answer_callback_query(call.id, 'Failed to reject order')
                    return

        bot.answer_callback_query(call.id)
        return

    @bot.message_handler(content_types=['photo'])
    @safe_handler
    def handle_photo(message: types.Message):
        user = message.from_user
        if db.is_banned(user.id):
            bot.reply_to(message, 'You are banned from using this bot.')
            return
        order = db.get_latest_awaiting_order(user.id)
        if not order:
            bot.reply_to(message, 'No awaiting order found. Please start a purchase first.')
            return
        file_id = message.photo[-1].file_id
        db.attach_receipt(order['id'], file_id)

        admin_id = db.get_setting('admin_id')
        admin_id = int(admin_id) if admin_id else None
        caption = (
            f"New payment receipt\n\nUser: {user.first_name or ''} {user.last_name or ''}\n"
            f"Username: @{user.username if user.username else '-'}\n"
            f"Telegram ID: {user.id}\n"
            f"Package: {order['package_title']}\n"
            f"Price: {format_currency(order['price'])}\n"
            f"Order ID: {order['id']}\n"
            f"Order Time: {order['created_at']}\n"
        )
        if admin_id:
            bot.send_photo(admin_id, file_id, caption=caption, reply_markup=kb.admin_order_actions(order['id']))
        bot.reply_to(message, '✅ Receipt received. Your order is pending verification by admin.')

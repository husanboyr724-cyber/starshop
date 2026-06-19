from telebot import types
from config import PACKAGES


class Keyboards:
    def __init__(self):
        pass

    def main_menu(self) -> types.InlineKeyboardMarkup:
        kb = types.InlineKeyboardMarkup(row_width=1)
        for p in PACKAGES:
            kb.add(types.InlineKeyboardButton(text=f"{p['title']} — {p['price']:,} UZS", callback_data=f"package:{p['key']}"))
        kb.add(types.InlineKeyboardButton(text="📦 My Orders", callback_data="my_orders"))
        kb.add(types.InlineKeyboardButton(text="📞 Admin", callback_data="contact_admin"))
        kb.add(types.InlineKeyboardButton(text="ℹ Help", callback_data="help"))
        return kb

    def package_page(self, package: dict) -> types.InlineKeyboardMarkup:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text="💳 Pay", callback_data=f"pay:{package['key']}"))
        kb.add(types.InlineKeyboardButton(text="📷 Send Receipt", callback_data="send_receipt"))
        kb.add(types.InlineKeyboardButton(text="⬅ Back", callback_data="back_to_main"))
        return kb

    def payment_keyboard(self) -> types.InlineKeyboardMarkup:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text="📷 Send Receipt", callback_data="send_receipt"))
        kb.add(types.InlineKeyboardButton(text="⬅ Back", callback_data="back_to_main"))
        return kb

    def admin_panel(self) -> types.InlineKeyboardMarkup:
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton(text="📊 Statistics", callback_data="admin:stats"), types.InlineKeyboardButton(text="👥 Users", callback_data="admin:users"))
        kb.add(types.InlineKeyboardButton(text="📦 Orders", callback_data="admin:orders"), types.InlineKeyboardButton(text="📢 Broadcast", callback_data="admin:broadcast"))
        kb.add(types.InlineKeyboardButton(text="💲 Edit Prices", callback_data="admin:prices"), types.InlineKeyboardButton(text="⚙ Settings", callback_data="admin:settings"))
        return kb

    def admin_order_actions(self, order_id: int) -> types.InlineKeyboardMarkup:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text="✅ Approve", callback_data=f"admin:approve:{order_id}"), types.InlineKeyboardButton(text="❌ Reject", callback_data=f"admin:reject:{order_id}"))
        return kb

    def back_keyboard(self) -> types.InlineKeyboardMarkup:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text="⬅ Back", callback_data="back_to_main"))
        return kb

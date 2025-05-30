from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def create_menu_layout(buttons: list, buttons_per_row: int = 2) -> InlineKeyboardMarkup:
    menu = InlineKeyboardMarkup(inline_keyboard=[])  # صراحتاً inline_keyboard را به عنوان لیست خالی تعریف می‌کنیم
    current_row = []
    for button in buttons:
        if button:
            current_row.append(button)
            if len(current_row) >= buttons_per_row:
                menu.inline_keyboard.append(current_row)
                current_row = []
    if current_row:
        menu.inline_keyboard.append(current_row)
    return menu


def main_menu(is_owner: bool) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text="➕ افزودن پنل جدید", callback_data="add_server"),
        None,
        InlineKeyboardButton(text="📌 مدیریت پنل‌ها", callback_data="manage_panels"),
        InlineKeyboardButton(text="👨‍💼 بخش مدیریت", callback_data="manage_admins") if is_owner else None
    ]
    return create_menu_layout([b for b in buttons if b], buttons_per_row=2)


def admin_management_menu() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text="➕ افزودن مدیر", callback_data="add_admin"),
        InlineKeyboardButton(text="🗑 حذف مدیر", callback_data="remove_admin"),
        InlineKeyboardButton(text="📊 اطلاعات کاربر", callback_data="user_info"),
        InlineKeyboardButton(text="📋 تنظیم کانال لاگ", callback_data="set_log_channel"),
        InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")
    ]
    return create_menu_layout(buttons, buttons_per_row=2)


def panel_login_menu() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")
    ]
    return create_menu_layout(buttons, buttons_per_row=1)


def panel_selection_menu(panels: list) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=f"📌 {alias}", callback_data=f"select_panel:{alias}")
        for alias, _, _, _, _ in panels
    ]
    buttons.extend([
        InlineKeyboardButton(text="🗑 حذف پنل", callback_data="delete_panel"),
        InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")
    ])
    return create_menu_layout(buttons, buttons_per_row=2)


def delete_panel_menu(panels: list) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=f"🗑 {alias}", callback_data=f"confirm_delete_panel:{alias}")
        for alias, _, _, _, _ in panels
    ]
    buttons.append(InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main"))
    return create_menu_layout(buttons, buttons_per_row=2)


def panel_action_menu() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text="🔍 جستجوی کاربر", callback_data="search_user"),
        InlineKeyboardButton(text="➕ ایجاد کاربر", callback_data="create_user"),
        InlineKeyboardButton(text="👥 کاربران", callback_data="list_users"),
        InlineKeyboardButton(text="🗑 حذف کاربران بدون حجم", callback_data="delete_exhausted_users"),
        InlineKeyboardButton(text="🔙 بازگشت به انتخاب پنل", callback_data="back_to_panel_selection")
    ]
    return create_menu_layout(buttons, buttons_per_row=2)


def users_list_menu(users: list, page: int = 0, limit: int = 21, total_count: int = None, stats: dict = None, total_pages: int = None) -> InlineKeyboardMarkup:
    def get_status_emoji(user):
        status = user.get('status', '').lower()
        expire = user.get('expire')
        data_limit = user.get('data_limit', 0) or 0
        used_traffic = user.get('used_traffic', 0) or 0
        import time
        now = int(time.time())
        if expire and expire > 0 and expire < now:
            return '⏰'
        if status == 'on_hold':
            return '🟠'
        if status == 'active':
            if data_limit > 0 and used_traffic >= data_limit:
                return '🚫'
            else:
                return '✅'
        elif status == 'disabled':
            return '⛔'
        else:
            return '❓'
    buttons = []
    for user in users:
        username = user.get('username', '-')
        emoji = get_status_emoji(user)
        buttons.append(InlineKeyboardButton(text=f"{emoji} {username}", callback_data=f"user_info:{username}"))
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ قبلی", callback_data=f"prev_users_page:{page-1}"))
    has_next = False
    if total_count is not None:
        if (page + 1) * limit < total_count:
            has_next = True
    elif len(users) == limit:
        has_next = True
    if has_next:
        nav_buttons.append(InlineKeyboardButton(text="بعدی ➡️", callback_data=f"next_users_page:{page+1}"))
    if nav_buttons:
        buttons.extend(nav_buttons)
    buttons.append(InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_panel_action_menu"))
    return create_menu_layout(buttons, buttons_per_row=3)


def user_action_menu(username: str) -> InlineKeyboardMarkup:
    menu = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 حذف کاربر", callback_data=f"delete_user:{username}"),
            InlineKeyboardButton(text="⚙️ مدیریت کانفیگ‌ها", callback_data=f"manage_configs:{username}")
        ],
        [
            InlineKeyboardButton(text="⛔ خاموش", callback_data=f"disable_user:{username}"),
            InlineKeyboardButton(text="✅ روشن", callback_data=f"enable_user:{username}")
        ],
        [
            InlineKeyboardButton(text="🗑 حذف کانفیگ‌ها", callback_data=f"delete_configs:{username}"),
            InlineKeyboardButton(text="🔄 تولید لینک جدید", callback_data=f"regenerate_link:{username}")
        ],
        [
            InlineKeyboardButton(text="📊 تنظیم حجم", callback_data=f"set_data_limit:{username}"),
            InlineKeyboardButton(text="⏰ تنظیم زمان انقضا", callback_data=f"set_expire_time:{username}")
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت به لیست کاربران", callback_data="back_to_users_list_menu")
        ]
    ])
    return menu


def note_menu() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text="📝 بدون یادداشت", callback_data="set_note_none"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_user_menu_note")
    ]
    return create_menu_layout(buttons, buttons_per_row=1)


def protocol_selection_menu(username: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text="VLESS", callback_data=f"select_protocol:vless:{username}"),
        InlineKeyboardButton(text="VMess", callback_data=f"select_protocol:vmess:{username}"),
        InlineKeyboardButton(text="Trojan", callback_data=f"select_protocol:trojan:{username}"),
        InlineKeyboardButton(text="Shadowsocks", callback_data=f"select_protocol:shadowsocks:{username}"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"back_to_user_menu:{username}")
    ]
    return create_menu_layout(buttons, buttons_per_row=2)


def config_selection_menu(available_inbounds: list, selected_inbounds: list, username: str) -> InlineKeyboardMarkup:
    import re
    menu = InlineKeyboardMarkup(inline_keyboard=[])  # صراحتاً inline_keyboard را به عنوان لیست خالی تعریف می‌کنیم
    current_row = []
    for inbound in available_inbounds:
        button_text = f"✅ {inbound}" if inbound in selected_inbounds else f"⬜ {inbound}"
        safe_inbound = re.sub(r'[^\w\-]', '_', inbound)
        callback_data = f"toggle_inbound:{safe_inbound}:{username}"
        button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
        current_row.append(button)
        if len(current_row) >= 2:
            menu.inline_keyboard.append(current_row)
            current_row = []
    if current_row:
        menu.inline_keyboard.append(current_row)
    menu.inline_keyboard.append([
        InlineKeyboardButton(text="✔️ تأیید", callback_data=f"confirm_inbounds_for_existing:{username}"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"back_to_user_menu:{username}")
    ])
    return menu

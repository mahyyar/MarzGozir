import aiohttp
import logging
import socket
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from typing import List, Tuple, Optional
from database.db import get_panels
from utils.formatting import format_traffic, format_expire_time
from bot.menus import main_menu, user_action_menu
from bot_config import ADMIN_IDS
from utils.message_utils import cleanup_messages
from aiogram.fsm.context import FSMContext
from aiogram import Bot, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

def is_owner(chat_id: int) -> bool:
    return chat_id in ADMIN_IDS

async def create_user_logic(chat_id: int, state: FSMContext, note: str) -> Tuple[Optional[str], Optional[str]]:
 
    data = await state.get_data()
    username = data.get("username")
    data_limit = data.get("data_limit")
    expire_time = data.get("expire_time")
    expire_days = data.get("expire_days")
    selected_panel_alias = data.get("selected_panel_alias")
    
    panels = get_panels(chat_id)
    panel = next((p for p in panels if p[0] == selected_panel_alias), None)
    if not panel:
        return None, "⚠️ پنل انتخاب‌شده یافت نشد."
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            headers = {"Authorization": f"Bearer {panel[2]}"}
            
            async with session.get(f"{panel[1].rstrip('/')}/api/inbounds", headers=headers) as response:
                inbounds_data = await response.json()
                if response.status != 200:
                    raise ValueError(f"دریافت اینباند‌ها ناموفق: {inbounds_data.get('detail', 'No details')}")
                inbounds_dict = {
                    protocol: [inbound['tag'] for inbound in settings]
                    for protocol, settings in inbounds_data.items()
                    if protocol in ["vless", "vmess"]
                }
            
            vless_id = str(uuid4())
            vmess_id = str(uuid4())
            user_data = {
                "username": username,
                "proxies": {
                    "vless": {"id": vless_id},
                    "vmess": {"id": vmess_id}
                },
                "inbounds": inbounds_dict,
                "data_limit": data_limit,
                "expire": expire_time,
                "note": note
            }
            
            async with session.post(f"{panel[1].rstrip('/')}/api/user", json=user_data, headers=headers) as response:
                result = await response.json()
                if response.status != 200:
                    raise ValueError(f"ایجاد کاربر ناموفق: {result.get('detail', 'No details')}")
            
            async with session.get(f"{panel[1].rstrip('/')}/api/user/{username}", headers=headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    subscription_url = user_data.get("subscription_url", "ناموجود")
                    return (
                        f"✅ کاربر '{username}' با موفقیت ایجاد شد!\n"
                        f"📊 حجم: {format_traffic(data_limit) if data_limit else 'نامحدود'}\n"
                        f"⏰ انقضا: {expire_days if expire_days > 0 else 'نامحدود'} روز\n"
                        f"🔗 لینک اشتراک: {subscription_url}",
                        None
                    )
                return "❌ نتوانستم لینک اشتراک را دریافت کنم.", None
    except Exception as e:
        logger.error(f"Create user error for {username}: {str(e)}")
        return None, f"❌ خطا در ایجاد کاربر: {str(e)}"

async def show_user_info(query: types.CallbackQuery, state: FSMContext, username: str, chat_id: int, selected_panel_alias: str, bot: Bot):
    await cleanup_messages(bot, chat_id, state)
    panels = get_panels(chat_id)
    panel = next((p for p in panels if p[0] == selected_panel_alias), None)
    if not panel:
        message = await bot.send_message(chat_id, "⚠️ پنل انتخاب‌شده یافت نشد.")
        await state.update_data(login_messages=[message.message_id])
        return
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            headers = {"Authorization": f"Bearer {panel[2]}"}
            async with session.get(f"{panel[1].rstrip('/')}/api/user/{username}", headers=headers) as response:
                if response.status != 200:
                    result = await response.json()
                    message = await bot.send_message(chat_id, f"❌ خطا در دریافت اطلاعات: {result.get('detail', 'کاربر یافت نشد')}")
                    await state.update_data(login_messages=[message.message_id])
                    return
                user = await response.json()
                protocols = ", ".join(user.get("proxies", {}).keys()) or "هیچ"
                response_text = (
                    f"👤 نام کاربری: {user['username']}\n"
                    f"📊 وضعیت: {user['status']}\n"
                    f"📈 حجم مصرفی: {format_traffic(user.get('used_traffic', 0))}\n"
                    f"📊 حجم کل: {format_traffic(user.get('data_limit', 0)) if user.get('data_limit') else 'نامحدود'}\n"
                    f"⏰ زمان انقضا: {format_expire_time(user.get('expire'))}\n"
                    f"📝 یادداشت: {user.get('note', 'هیچ')}\n"
                    f"🔌 پروتکل‌ها: {protocols}\n"
                    f"🔗 لینک اشتراک: {user.get('subscription_url', 'ناموجود')}"
                )
                message = await bot.send_message(chat_id, response_text, reply_markup=user_action_menu(username))
                await state.update_data(login_messages=[message.message_id])
    except Exception as e:
        logger.error(f"Show user info error for {username}: {str(e)}")
        message = await bot.send_message(chat_id, f"❌ خطا در نمایش اطلاعات: {str(e)}")
        await state.update_data(login_messages=[message.message_id])

async def delete_user_logic(query: types.CallbackQuery, state: FSMContext, username: str, chat_id: int, bot: Bot):
 
    await cleanup_messages(bot, chat_id, state)
    data = await state.get_data()
    selected_panel_alias = data.get("selected_panel_alias")
    if not selected_panel_alias:
        message = await bot.send_message(chat_id, "⚠️ لطفاً ابتدا یک پنل انتخاب کنید.", reply_markup=main_menu(is_owner(chat_id)))
        await state.update_data(login_messages=[message.message_id])
        await state.clear()
        return
    
    panels = get_panels(chat_id)
    panel = next((p for p in panels if p[0] == selected_panel_alias), None)
    if not panel:
        message = await bot.send_message(chat_id, "⚠️ پنل انتخاب‌شده یافت نشد.")
        await state.update_data(login_messages=[message.message_id])
        return
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            headers = {"Authorization": f"Bearer {panel[2]}"}
            async with session.delete(f"{panel[1].rstrip('/')}/api/user/{username}", headers=headers) as response:
                if response.status == 200:
                    message = await bot.send_message(chat_id, f"🗑 کاربر '{username}' با موفقیت حذف شد.", reply_markup=main_menu(is_owner(chat_id)))
                    await state.update_data(login_messages=[message.message_id])
                else:
                    result = await response.json()
                    raise ValueError(f"حذف کاربر ناموفق: {result.get('detail', 'No details')}")
    except Exception as e:
        logger.error(f"Delete user error for {username}: {str(e)}")
        message = await bot.send_message(chat_id, f"❌ خطا در حذف کاربر: {str(e)}")
        await state.update_data(login_messages=[message.message_id])
    await state.clear()

async def disable_user_logic(query: types.CallbackQuery, state: FSMContext, username: str, chat_id: int, bot: Bot):

    await cleanup_messages(bot, chat_id, state)
    data = await state.get_data()
    selected_panel_alias = data.get("selected_panel_alias")
    if not selected_panel_alias:
        message = await bot.send_message(chat_id, "⚠️ لطفاً ابتدا یک پنل انتخاب کنید.", reply_markup=main_menu(is_owner(chat_id)))
        await state.update_data(login_messages=[message.message_id])
        await state.clear()
        return
    
    panels = get_panels(chat_id)
    panel = next((p for p in panels if p[0] == selected_panel_alias), None)
    if not panel:
        message = await bot.send_message(chat_id, "⚠️ پنل انتخاب‌شده یافت نشد.")
        await state.update_data(login_messages=[message.message_id])
        return
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            headers = {"Authorization": f"Bearer {panel[2]}", "Content-Type": "application/json"}
            async with session.get(f"{panel[1].rstrip('/')}/api/user/{username}", headers=headers) as response:
                if response.status != 200:
                    raise ValueError("کاربر یافت نشد")
                current_user = await response.json()
            
            current_user["status"] = "disabled"
            async with session.put(f"{panel[1].rstrip('/')}/api/user/{username}", json=current_user, headers=headers) as response:
                if response.status == 200:
                    message = await bot.send_message(chat_id, f"⏹ کاربر '{username}' با موفقیت غیرفعال شد.")
                    await state.update_data(login_messages=[message.message_id])
                    await show_user_info(query, state, username, chat_id, selected_panel_alias, bot)
                else:
                    result = await response.json()
                    raise ValueError(f"خاموش کردن کاربر ناموفق: {result.get('detail', 'No details')}")
    except Exception as e:
        logger.error(f"Disable user error for {username}: {str(e)}")
        message = await bot.send_message(chat_id, f"❌ خطا در غیرفعال کردن کاربر: {str(e)}")
        await state.update_data(login_messages=[message.message_id])

async def enable_user_logic(query: types.CallbackQuery, state: FSMContext, username: str, chat_id: int, bot: Bot):
    await cleanup_messages(bot, chat_id, state)
    data = await state.get_data()
    selected_panel_alias = data.get("selected_panel_alias")
    if not selected_panel_alias:
        message = await bot.send_message(chat_id, "⚠️ لطفاً ابتدا یک پنل انتخاب کنید.", reply_markup=main_menu(is_owner(chat_id)))
        await state.update_data(login_messages=[message.message_id])
        await state.clear()
        return
    
    panels = get_panels(chat_id)
    panel = next((p for p in panels if p[0] == selected_panel_alias), None)
    if not panel:
        message = await bot.send_message(chat_id, "⚠️ پنل انتخاب‌شده یافت نشد.")
        await state.update_data(login_messages=[message.message_id])
        return
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            headers = {"Authorization": f"Bearer {panel[2]}", "Content-Type": "application/json"}
            async with session.get(f"{panel[1].rstrip('/')}/api/user/{username}", headers=headers) as response:
                if response.status != 200:
                    raise ValueError("کاربر یافت نشد")
                current_user = await response.json()
            
            current_user["status"] = "active"
            async with session.put(f"{panel[1].rstrip('/')}/api/user/{username}", json=current_user, headers=headers) as response:
                if response.status == 200:
                    message = await bot.send_message(chat_id, f"▶️ کاربر '{username}' با موفقیت فعال شد.")
                    await state.update_data(login_messages=[message.message_id])
                    await show_user_info(query, state, username, chat_id, selected_panel_alias, bot)
                else:
                    result = await response.json()
                    raise ValueError(f"روشن کردن کاربر ناموفق: {result.get('detail', 'No details')}")
    except Exception as e:
        logger.error(f"Enable user error for {username}: {str(e)}")
        message = await bot.send_message(chat_id, f"❌ خطا در فعال کردن کاربر: {str(e)}")
        await state.update_data(login_messages=[message.message_id])

async def delete_configs_logic(query: types.CallbackQuery, state: FSMContext, username: str, chat_id: int, bot: Bot):
 
    await cleanup_messages(bot, chat_id, state)
    data = await state.get_data()
    selected_panel_alias = data.get("selected_panel_alias")
    if not selected_panel_alias:
        message = await bot.send_message(chat_id, "⚠️ لطفاً ابتدا یک پنل انتخاب کنید.", reply_markup=main_menu(is_owner(chat_id)))
        await state.update_data(login_messages=[message.message_id])
        await state.clear()
        return
    
    panels = get_panels(chat_id)
    panel = next((p for p in panels if p[0] == selected_panel_alias), None)
    if not panel:
        message = await bot.send_message(chat_id, "⚠️ پنل انتخاب‌شده یافت نشد.")
        await state.update_data(login_messages=[message.message_id])
        return
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            headers = {"Authorization": f"Bearer {panel[2]}", "Content-Type": "application/json"}
            async with session.get(f"{panel[1].rstrip('/')}/api/user/{username}", headers=headers) as response:
                if response.status != 200:
                    message = await bot.send_message(chat_id, "❌ کاربر یافت نشد.")
                    await state.update_data(login_messages=[message.message_id])
                    return
                current_user = await response.json()
            
            current_user["inbounds"] = {}
            async with session.put(f"{panel[1].rstrip('/')}/api/user/{username}", json=current_user, headers=headers) as response:
                if response.status == 200:
                    message = await bot.send_message(chat_id, f"🗑 همه کانفیگ‌های کاربر '{username}' با موفقیت حذف شد.")
                    await state.update_data(login_messages=[message.message_id])
                    await show_user_info(query, state, username, chat_id, selected_panel_alias, bot)
                else:
                    result = await response.json()
                    message = await bot.send_message(chat_id, f"❌ خطا در حذف کانفیگ‌ها: {result.get('detail', 'No details')}")
                    await state.update_data(login_messages=[message.message_id])
    except Exception as e:
        logger.error(f"Error deleting configs for {username}: {str(e)}")
        message = await bot.send_message(chat_id, f"❌ خطا: {str(e)}")
        await state.update_data(login_messages=[message.message_id])

async def fetch_users_batch(panel_url: str, token: str, offset: int, limit: int) -> List[dict]:
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            headers = {"Authorization": f"Bearer {token}"}
            params = {"offset": offset, "limit": limit}
            async with session.get(f"{panel_url.rstrip('/')}/api/users", headers=headers, params=params) as response:
                if response.status != 200:
                    result = await response.json()
                    raise ValueError(f"دریافت کاربران ناموفق: {result.get('detail', 'No details')}")
                users_data = await response.json()
                if "users" not in users_data:
                    raise ValueError("پاسخ API شامل کلید 'users' نیست")
                return users_data.get("users", [])
    except Exception as e:
        logger.error(f"Error fetching users batch (offset={offset}, limit={limit}): {str(e)}")
        raise

async def get_users_stats(panel_url: str, token: str, force_refresh: bool = False) -> dict:
    from utils.cache import get_users_stats_cache, set_users_stats_cache
    from bot_config import CACHE_DURATION
    
    cache_key = f"{panel_url}:{token}"
    if not force_refresh:
        cached_stats = get_users_stats_cache(panel_url, token, CACHE_DURATION)
        if cached_stats:
            return cached_stats
    
    stats = {"total": 0, "active": 0, "inactive": 0, "expired": 0, "limited": 0}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
            headers = {"Authorization": f"Bearer {token}"}
            async with session.get(f"{panel_url.rstrip('/')}/api/stats", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    required_keys = ["total", "active", "inactive", "expired", "limited"]
                    stats = {key: data.get(key, 0) for key in required_keys}
                else:
                    raise ValueError("Failed to fetch stats from /api/stats")
    except Exception:
        try:
            offset = 0
            limit = 200
            now = int(datetime.now(timezone.utc).timestamp())
            while True:
                users = await fetch_users_batch(panel_url, token, offset, limit)
                if not users:
                    break
                stats["total"] += len(users)
                for user in users:
                    username = user.get("username", "unknown")
                    if not all(key in user for key in ["status", "expire", "data_limit", "used_traffic"]):
                        logger.warning(f"Incomplete user data for {username}: {user}")
                    if user.get("status") == "active":
                        stats["active"] += 1
                    elif user.get("status") in ["disabled", "on_hold"]:
                        stats["inactive"] += 1
                    expire_time = user.get("expire", 0) or 0
                    if expire_time > 0 and expire_time < now:
                        stats["expired"] += 1
                    data_limit = user.get("data_limit", 0) or 0
                    used_traffic = user.get("used_traffic", 0) or 0
                    if data_limit > 0 and used_traffic >= data_limit:
                        stats["limited"] += 1
                offset += limit
        except Exception as e:
            logger.error(f"Manual count failed: {str(e)}")
            return stats
    
    set_users_stats_cache(panel_url, token, stats)
    return stats

async def request_delete_confirmation(chat_id: int, action: str, selected_panel_alias: str, bot: Bot, state: FSMContext):
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تأیید", callback_data=f"confirm_delete:{action}:{selected_panel_alias}"),
            InlineKeyboardButton(text="❌ لغو", callback_data=f"cancel_delete:{selected_panel_alias}")
        ]
    ])
    message = await bot.send_message(
        chat_id,
        f"آیا مطمئنید که می‌خواهید کاربران {'منقضی‌شده' if action == 'expired' else 'بدون حجم'} را حذف کنید؟",
        reply_markup=confirm_keyboard
    )
    await state.update_data(login_messages=[message.message_id], pending_delete_action=action)

async def delete_expired_users(chat_id: int, selected_panel_alias: str, bot: Bot, state: FSMContext, confirm: bool = False) -> bool:
    if not confirm:
        await request_delete_confirmation(chat_id, "expired", selected_panel_alias, bot, state)
        return False
    
    panels = get_panels(chat_id)
    panel = next((p for p in panels if p[0] == selected_panel_alias), None)
    if not panel:
        await bot.send_message(chat_id, "⚠️ پنل انتخاب‌شده یافت نشد.")
        return False
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            headers = {"Authorization": f"Bearer {panel[2]}"}
            offset = 0
            limit = 100 
            now = int(datetime.now(timezone.utc).timestamp())
            deleted_count = 0
            deleted_users = []
            
            while True:
                params = {"offset": offset, "limit": limit}
                async with session.get(f"{panel[1].rstrip('/')}/api/users", headers=headers, params=params) as response:
                    if response.status != 200:
                        result = await response.json()
                        await bot.send_message(chat_id, f"❌ خطا در دریافت کاربران: {result.get('detail', 'No details')}")
                        return False
                    users_data = await response.json()
                    users = users_data.get("users", [])
                    if not users:
                        break
                    for user in users:
                        expire_time = user.get("expire", 0) or 0
                        if expire_time > 0 and expire_time < now:
                            username = user.get("username", "unknown")
                            async with session.delete(f"{panel[1].rstrip('/')}/api/user/{username}", headers=headers) as delete_response:
                                if delete_response.status == 200:
                                    deleted_count += 1
                                    deleted_users.append(username)
                                else:
                                    logger.warning(f"Failed to delete user {username}: {await delete_response.json()}")
                    offset += limit
            
            response_text = f"🗑 {deleted_count} کاربر با زمان منقضی با موفقیت حذف شدند."
            if deleted_users:
                response_text += f"\nکاربران حذف‌شده: {', '.join(deleted_users[:10])}{'...' if len(deleted_users) > 10 else ''}"
            await bot.send_message(chat_id, response_text)
            return True
    except Exception as e:
        logger.error(f"Error deleting expired users: {str(e)}")
        await bot.send_message(chat_id, f"❌ خطا در حذف کاربران منقضی: {str(e)}")
        return False

async def delete_data_exhausted_users(chat_id: int, selected_panel_alias: str, bot: Bot, state: FSMContext, confirm: bool = False) -> bool:
    if not confirm:
        await request_delete_confirmation(chat_id, "exhausted", selected_panel_alias, bot, state)
        return False
    
    panels = get_panels(chat_id)
    panel = next((p for p in panels if p[0] == selected_panel_alias), None)
    if not panel:
        await bot.send_message(chat_id, "⚠️ پنل انتخاب‌شده یافت نشد.")
        return False
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            headers = {"Authorization": f"Bearer {panel[2]}"}
            offset = 0
            limit = 100 
            deleted_count = 0
            deleted_users = []
            
            while True:
                params = {"offset": offset, "limit": limit}
                async with session.get(f"{panel[1].rstrip('/')}/api/users", headers=headers, params=params) as response:
                    if response.status != 200:
                        result = await response.json()
                        await bot.send_message(chat_id, f"❌ خطا در دریافت کاربران: {result.get('detail', 'No details')}")
                        return False
                    users_data = await response.json()
                    users = users_data.get("users", [])
                    if not users:
                        break
                    for user in users:
                        data_limit = user.get("data_limit", 0) or 0
                        used_traffic = user.get("used_traffic", 0) or 0
                        if data_limit > 0 and used_traffic >= data_limit:
                            username = user.get("username", "unknown")
                            async with session.delete(f"{panel[1].rstrip('/')}/api/user/{username}", headers=headers) as delete_response:
                                if delete_response.status == 200:
                                    deleted_count += 1
                                    deleted_users.append(username)
                                else:
                                    logger.warning(f"Failed to delete user {username}: {await delete_response.json()}")
                    offset += limit
            
            response_text = f"🗑 {deleted_count} کاربر با حجم مصرف‌شده با موفقیت حذف شدند."
            if deleted_users:
                response_text += f"\nکاربران حذف‌شده: {', '.join(deleted_users[:10])}{'...' if len(deleted_users) > 10 else ''}"
            await bot.send_message(chat_id, response_text)
            return True
    except Exception as e:
        logger.error(f"Error deleting data exhausted users: {str(e)}")
        await bot.send_message(chat_id, f"❌ خطا در حذف کاربران با حجم مصرف‌شده: {str(e)}")
        return False

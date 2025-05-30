import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.bot import DefaultBotProperties
from bot.handlers import start, button_callback, message_handler
from bot_config import TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    session = AiohttpSession(timeout=30)
    bot = Bot(token=TOKEN, session=session, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(max_retries=5, retry_delay=2)
    
    dp.message.register(start, Command(commands=["start"]))
    dp.callback_query.register(button_callback)
    dp.message.register(message_handler)
    try:
        logger.info("Starting bot...")
        await dp.start_polling(bot, polling_timeout=20)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    from database.db import init_db
    init_db()
    import asyncio
    asyncio.run(main())

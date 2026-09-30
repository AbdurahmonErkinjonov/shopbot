import asyncio
import logging
from aiogram import Bot
from config import config
from models import init_models
from bot import build_dispatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Initializing database schema...")
    await init_models()

    bot = Bot(token=config.BOT_TOKEN)
    dp = build_dispatcher()

    logger.info("Starting Telegram Bot (Polling mode)...")
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot execution stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot shutdown requested.")

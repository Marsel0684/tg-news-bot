"""
Telegram News Bot — точка входа.
Запуск: python main.py
"""

import logging
import asyncio
from scheduler import run_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("🚀 Запуск Telegram News Bot...")
    try:
        asyncio.run(run_scheduler())
    except KeyboardInterrupt:
        logger.info("⛔ Бот остановлен вручную.")

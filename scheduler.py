"""
scheduler.py — планировщик запусков.
"""

import logging
import asyncio
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import (
    PARSE_INTERVAL_MINUTES,
    QUIET_HOURS_START,
    QUIET_HOURS_END,
    validate_config,
)
from database import init_db, cleanup_old_records, save_run_stats, get_stats_last_7_days
from parser import parse_all_sources
from filter import filter_items
from poster import post_new_items

logger = logging.getLogger(__name__)


def _is_quiet_hours() -> bool:
    """Проверяем, находимся ли в часах тишины (по UTC+5 / МСК примерно)."""
    now_hour = datetime.now().hour  # локальное время сервера
    if QUIET_HOURS_START > QUIET_HOURS_END:
        # Переход через полночь: 23..00..07
        return now_hour >= QUIET_HOURS_START or now_hour < QUIET_HOURS_END
    else:
        return QUIET_HOURS_START <= now_hour < QUIET_HOURS_END


async def run_once() -> None:
    """Один прогон: парсинг → фильтрация → публикация."""
    logger.info("=" * 50)
    logger.info("🔄 Начало прогона")

    if _is_quiet_hours():
        logger.info(f"🌙 Часы тишины ({QUIET_HOURS_START}:00–{QUIET_HOURS_END}:00) — пропускаем")
        return

    # 1. Парсинг
    raw_items = await parse_all_sources()

    # 2. Фильтрация
    relevant_items = filter_items(raw_items)

    if not relevant_items:
        logger.info("Релевантных новостей не найдено")
        save_run_stats(parsed=len(raw_items), posted=0, skipped=0)
        return

    # 3. Публикация
    posted, skipped = await post_new_items(relevant_items)

    # 4. Статистика
    save_run_stats(parsed=len(raw_items), posted=posted, skipped=skipped + (len(relevant_items) - posted - skipped))

    logger.info(f"✅ Прогон завершён: {posted} опубликовано, {skipped} пропущено")
    logger.info("=" * 50)

    # Периодическая очистка старых записей
    cleanup_old_records()


async def run_scheduler() -> None:
    """Инициализация и запуск планировщика."""
    # Валидация конфига
    validate_config()

    # Инициализация базы
    init_db()

    # Статистика за неделю при старте
    stats = get_stats_last_7_days()
    logger.info(
        f"📊 Статистика за 7 дней: {stats['runs']} прогонов, {stats['posted']} постов"
    )

    # Первый прогон сразу при старте
    logger.info("▶️ Первый прогон при запуске...")
    await run_once()

    # Планировщик
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_once,
        trigger=IntervalTrigger(minutes=PARSE_INTERVAL_MINUTES),
        id="news_job",
        name=f"Парсинг новостей каждые {PARSE_INTERVAL_MINUTES} мин",
        misfire_grace_time=60,
    )
    scheduler.start()

    logger.info(
        f"⏰ Планировщик запущен: интервал {PARSE_INTERVAL_MINUTES} мин"
    )

    # Держим процесс живым
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Планировщик остановлен")

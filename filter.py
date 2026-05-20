"""
filter.py — фильтрация новостей по ключевым словам и релевантности.
"""

import logging
from parser import NewsItem
from config import INCLUDE_KEYWORDS, EXCLUDE_KEYWORDS

logger = logging.getLogger(__name__)


def _text_for_check(item: NewsItem) -> str:
    """Объединяем заголовок + саммари для проверки."""
    return (item.title + " " + item.summary).lower()


def is_relevant(item: NewsItem) -> bool:
    """
    Возвращает True, если новость релевантна нашей тематике.
    Логика:
      1. Если есть стоп-слово — сразу False.
      2. Если есть хотя бы одно из include-слов — True.
    """
    text = _text_for_check(item)

    # Проверка стоп-слов
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in text:
            logger.debug(f"Отфильтровано (стоп-слово '{kw}'): {item.title[:60]}")
            return False

    # Проверка включающих ключевых слов
    for kw in INCLUDE_KEYWORDS:
        if kw.lower() in text:
            return True

    logger.debug(f"Отфильтровано (нет ключевых слов): {item.title[:60]}")
    return False


def deduplicate_by_title(items: list[NewsItem]) -> list[NewsItem]:
    """
    Убираем дубликаты внутри одного прогона по похожести заголовков.
    Простая эвристика: первые 40 символов заголовка.
    """
    seen_keys: set[str] = set()
    unique: list[NewsItem] = []
    for item in items:
        key = item.title[:40].lower().strip()
        if key not in seen_keys:
            seen_keys.add(key)
            unique.append(item)
    return unique


def filter_items(items: list[NewsItem]) -> list[NewsItem]:
    """Полный цикл фильтрации: дедупликация + релевантность."""
    # Шаг 1: убираем дубликаты заголовков внутри текущего прогона
    items = deduplicate_by_title(items)

    # Шаг 2: проверяем релевантность
    relevant = [item for item in items if is_relevant(item)]

    logger.info(
        f"Фильтрация: {len(items)} → {len(relevant)} релевантных"
    )
    return relevant

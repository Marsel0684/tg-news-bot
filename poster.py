"""
poster.py — форматирование и отправка постов в Telegram-канал.
"""

import logging
import asyncio
import httpx
from parser import NewsItem
from database import mark_as_sent, is_already_sent
from config import BOT_TOKEN, CHANNEL_ID, MAX_POSTS_PER_RUN

logger = logging.getLogger(__name__)

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def format_post(item: NewsItem) -> str:
    """
    Форматируем новость в Telegram-пост.
    Используем HTML-разметку (parse_mode=HTML).
    """
    lines = []

    # Заголовок
    lines.append(f"{item.source_emoji} <b>{_escape(item.title)}</b>")
    lines.append("")

    # Краткое описание (если есть)
    if item.summary and len(item.summary) > 40:
        summary = item.summary[:280].strip()
        if len(item.summary) > 280:
            summary += "…"
        lines.append(f"{_escape(summary)}")
        lines.append("")

    # Источник + ссылка
    lines.append(f"🔗 <a href=\"{item.url}\">{_escape(item.source_name)}</a>")

    # Хэштеги
    lines.append("")
    lines.append(_make_hashtags(item))

    return "\n".join(lines)


def _escape(text: str) -> str:
    """Экранируем HTML-спецсимволы."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _make_hashtags(item: NewsItem) -> str:
    """Генерируем хэштеги на основе источника и языка."""
    tags = ["#новости"]
    name_lower = item.source_name.lower()

    if "marketing" in name_lower or "маркетинг" in name_lower or "cossa" in name_lower:
        tags.append("#маркетинг")
    if "target" in name_lower or "search engine" in name_lower:
        tags.append("#таргетинг")
    if "adindex" in name_lower or "adweek" in name_lower or "sostav" in name_lower:
        tags.append("#реклама")
    if "social" in name_lower or "SMM" in name_lower:
        tags.append("#SMM")
    if "vc.ru" in name_lower or "spark" in name_lower:
        tags.append("#инфобизнес")

    tags.append("#digitalmarketing")
    return " ".join(tags)


async def send_to_channel(item: NewsItem, client: httpx.AsyncClient) -> bool:
    """
    Отправляем один пост в канал.
    Если есть картинка — sendPhoto, иначе sendMessage.
    """
    text = format_post(item)

    # Если картинка доступна — пробуем sendPhoto
    if item.image_url:
        success = await _send_photo(item, text, client)
        if success:
            return True
        # Fallback на текст если фото не получилось

    return await _send_message(text, client)


async def _send_message(text: str, client: httpx.AsyncClient) -> bool:
    try:
        resp = await client.post(
            f"{TG_API}/sendMessage",
            json={
                "chat_id": CHANNEL_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=20,
        )
        data = resp.json()
        if data.get("ok"):
            return True
        else:
            logger.error(f"Telegram API ошибка: {data.get('description')}")
            return False
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        return False


async def _send_photo(item: NewsItem, caption: str, client: httpx.AsyncClient) -> bool:
    try:
        resp = await client.post(
            f"{TG_API}/sendPhoto",
            json={
                "chat_id": CHANNEL_ID,
                "photo": item.image_url,
                "caption": caption[:1024],  # лимит caption в TG
                "parse_mode": "HTML",
            },
            timeout=20,
        )
        data = resp.json()
        return data.get("ok", False)
    except Exception as e:
        logger.debug(f"Не удалось отправить фото: {e}")
        return False


async def post_new_items(items: list[NewsItem]) -> tuple[int, int]:
    """
    Главная функция постинга.
    Возвращает (posted_count, skipped_count).
    """
    posted = 0
    skipped = 0

    async with httpx.AsyncClient() as client:
        for item in items:
            if posted >= MAX_POSTS_PER_RUN:
                logger.info(f"Достигнут лимит MAX_POSTS_PER_RUN={MAX_POSTS_PER_RUN}")
                break

            # Проверяем базу данных (дедупликация между прогонами)
            if is_already_sent(item.url):
                skipped += 1
                continue

            success = await send_to_channel(item, client)

            if success:
                mark_as_sent(item.url, item.title, item.source_name)
                posted += 1
                logger.info(f"✅ Опубликовано: {item.title[:60]}")
                # Пауза между постами — чтобы не флудить
                await asyncio.sleep(3)
            else:
                logger.warning(f"❌ Не удалось опубликовать: {item.title[:60]}")

    return posted, skipped

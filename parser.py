"""
parser.py — парсинг RSS-лент и Telegram-каналов.
"""

import asyncio
import logging
import feedparser
import httpx
from dataclasses import dataclass
from datetime import datetime
from bs4 import BeautifulSoup
from config import RSS_SOURCES, HTTP_PROXY, TG_CHANNELS_TO_PARSE

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    title: str
    url: str
    summary: str
    source_name: str
    source_emoji: str
    published_at: datetime | None = None
    image_url: str | None = None


def _clean_html(raw: str) -> str:
    """Убираем HTML-теги, оставляем чистый текст."""
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    # Обрезаем до 300 символов
    return text[:300] + ("…" if len(text) > 300 else "")


def _extract_image(entry) -> str | None:
    """Пытаемся вытащить превью-картинку из RSS-записи."""
    # media:content
    media = getattr(entry, "media_content", None)
    if media and isinstance(media, list) and media[0].get("url"):
        return media[0]["url"]
    # enclosures
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image"):
                return enc.get("href") or enc.get("url")
    # og:image из summary html
    summary_raw = getattr(entry, "summary", "")
    if summary_raw:
        soup = BeautifulSoup(summary_raw, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]
    return None


def _parse_date(entry) -> datetime | None:
    published = getattr(entry, "published_parsed", None)
    if published:
        try:
            return datetime(*published[:6])
        except Exception:
            pass
    return None


def parse_rss_source(source: dict) -> list[NewsItem]:
    """Синхронный парсинг одного RSS-источника."""
    name = source["name"]
    url = source["url"]
    emoji = source.get("emoji", "📰")
    items: list[NewsItem] = []

    try:
        proxies = {"http://": HTTP_PROXY, "https://": HTTP_PROXY} if HTTP_PROXY else None
        # feedparser умеет сам делать HTTP, но мы контролируем прокси
        headers = {"User-Agent": "Mozilla/5.0 TelegramNewsBot/1.0"}

        if HTTP_PROXY:
            import urllib.request
            proxy_handler = urllib.request.ProxyHandler({"http": HTTP_PROXY, "https": HTTP_PROXY})
            opener = urllib.request.build_opener(proxy_handler)
            feed_data = opener.open(url, timeout=15).read()
            feed = feedparser.parse(feed_data)
        else:
            feed = feedparser.parse(url, agent=headers["User-Agent"], request_headers=headers)

        if feed.bozo and not feed.entries:
            logger.warning(f"[{name}] Плохой RSS (bozo): {feed.bozo_exception}")
            return []

        for entry in feed.entries[:20]:  # берём максимум 20 свежих
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()

            if not title or not link:
                continue

            summary_raw = entry.get("summary") or entry.get("description") or ""
            summary = _clean_html(summary_raw)
            image = _extract_image(entry)
            published = _parse_date(entry)

            items.append(
                NewsItem(
                    title=title,
                    url=link,
                    summary=summary,
                    source_name=name,
                    source_emoji=emoji,
                    published_at=published,
                    image_url=image,
                )
            )

        logger.info(f"[{name}] Получено: {len(items)} записей")

    except Exception as e:
        logger.error(f"[{name}] Ошибка парсинга: {e}")

    return items


async def parse_all_sources() -> list[NewsItem]:
    """Асинхронно парсим все RSS-источники."""
    loop = asyncio.get_event_loop()

    tasks = [
        loop.run_in_executor(None, parse_rss_source, src)
        for src in RSS_SOURCES
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items: list[NewsItem] = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Исключение при парсинге: {result}")
        elif isinstance(result, list):
            all_items.extend(result)

    # Если настроены Telegram-каналы — парсим через Telethon
    if TG_CHANNELS_TO_PARSE:
        tg_items = await parse_telegram_channels()
        all_items.extend(tg_items)

    logger.info(f"Итого собрано новостей: {len(all_items)}")
    return all_items


# ── Telethon-парсинг Telegram-каналов (опционально) ───────

async def parse_telegram_channels() -> list[NewsItem]:
    """
    Парсинг открытых Telegram-каналов через Telethon.
    Требует TELETHON_API_ID и TELETHON_API_HASH в .env
    """
    from config import TELETHON_API_ID, TELETHON_API_HASH

    if not TELETHON_API_ID or not TELETHON_API_HASH:
        logger.debug("Telethon не настроен — пропускаем TG-каналы")
        return []

    try:
        from telethon import TelegramClient
        from telethon.tl.functions.messages import GetHistoryRequest
    except ImportError:
        logger.warning("telethon не установлен. pip install telethon")
        return []

    items: list[NewsItem] = []

    async with TelegramClient("tg_parser", int(TELETHON_API_ID), TELETHON_API_HASH) as client:
        for channel_username in TG_CHANNELS_TO_PARSE:
            try:
                channel = await client.get_entity(channel_username)
                history = await client(GetHistoryRequest(
                    peer=channel,
                    limit=20,
                    offset_date=None,
                    offset_id=0,
                    max_id=0,
                    min_id=0,
                    add_offset=0,
                    hash=0,
                ))
                for msg in history.messages:
                    if not msg.message:
                        continue
                    text = msg.message.strip()
                    if len(text) < 30:
                        continue
                    title = text.split("\n")[0][:120]
                    # Формируем ссылку на пост
                    url = f"https://t.me/{channel_username.lstrip('@')}/{msg.id}"
                    items.append(NewsItem(
                        title=title,
                        url=url,
                        summary=text[:300],
                        source_name=channel_username,
                        source_emoji="📣",
                        published_at=msg.date,
                    ))
                logger.info(f"[{channel_username}] TG: {len(history.messages)} сообщений")
            except Exception as e:
                logger.error(f"[{channel_username}] Telethon ошибка: {e}")

    return items

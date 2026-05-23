"""
parser.py — парсинг RSS-лент и публичных Telegram-каналов через t.me/s/
Telethon не требуется.
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36"
}


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
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return text[:300] + ("…" if len(text) > 300 else "")


def _extract_image(entry) -> str | None:
    media = getattr(entry, "media_content", None)
    if media and isinstance(media, list) and media[0].get("url"):
        return media[0]["url"]
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image"):
                return enc.get("href") or enc.get("url")
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


# ── RSS ───────────────────────────────────────────────────

def parse_rss_source(source: dict) -> list[NewsItem]:
    name = source["name"]
    url = source["url"]
    emoji = source.get("emoji", "📰")
    items: list[NewsItem] = []

    try:
        if HTTP_PROXY:
            import urllib.request
            proxy_handler = urllib.request.ProxyHandler(
                {"http": HTTP_PROXY, "https": HTTP_PROXY}
            )
            opener = urllib.request.build_opener(proxy_handler)
            feed_data = opener.open(url, timeout=15).read()
            feed = feedparser.parse(feed_data)
        else:
            feed = feedparser.parse(url, request_headers=HEADERS)

        if feed.bozo and not feed.entries:
            logger.warning(f"[{name}] Плохой RSS: {feed.bozo_exception}")
            return []

        for entry in feed.entries[:20]:
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            if not title or not link:
                continue

            summary = _clean_html(
                entry.get("summary") or entry.get("description") or ""
            )
            items.append(NewsItem(
                title=title,
                url=link,
                summary=summary,
                source_name=name,
                source_emoji=emoji,
                published_at=_parse_date(entry),
                image_url=_extract_image(entry),
            ))

        logger.info(f"[{name}] RSS: {len(items)} записей")

    except Exception as e:
        logger.error(f"[{name}] Ошибка RSS: {e}")

    return items


# ── Telegram web (t.me/s/) — без Telethon ─────────────────

def parse_tg_channel_web(channel: str) -> list[NewsItem]:
    """
    Парсинг публичного Telegram-канала через t.me/s/username.
    Работает без API-ключей для любого публичного канала.
    """
    username = channel.lstrip("@")
    url = f"https://t.me/s/{username}"
    items: list[NewsItem] = []

    try:
        resp = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        if resp.status_code != 200:
            logger.warning(f"[{channel}] HTTP {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        messages = soup.find_all("div", class_="tgme_widget_message_wrap")

        if not messages:
            logger.warning(f"[{channel}] Посты не найдены — канал закрытый или пустой")
            return []

        for msg in messages[-20:]:  # последние 20 постов
            # Текст поста
            text_el = msg.find("div", class_="tgme_widget_message_text")
            if not text_el:
                continue
            text = text_el.get_text(separator=" ", strip=True)
            if len(text) < 30:
                continue

            # Ссылка на пост
            link_el = msg.find("a", class_="tgme_widget_message_date")
            post_url = link_el["href"] if link_el else url

            # Картинка (если есть)
            image_url = None
            img_el = msg.find("a", class_="tgme_widget_message_photo_wrap")
            if img_el and img_el.get("style"):
                style = img_el["style"]
                if "url(" in style:
                    image_url = style.split("url(")[1].split(")")[0].strip("'\"")

            # Заголовок = первая строка текста
            title = text.split("\n")[0][:150].strip()
            summary = text[:300]

            items.append(NewsItem(
                title=title,
                url=post_url,
                summary=summary,
                source_name=f"@{username}",
                source_emoji="📣",
                image_url=image_url,
            ))

        logger.info(f"[{channel}] TG web: {len(items)} постов")

    except Exception as e:
        logger.error(f"[{channel}] Ошибка TG web парсинга: {e}")

    return items


# ── Главная функция ────────────────────────────────────────

async def parse_all_sources() -> list[NewsItem]:
    loop = asyncio.get_event_loop()

    # RSS источники — параллельно
    rss_tasks = [
        loop.run_in_executor(None, parse_rss_source, src)
        for src in RSS_SOURCES
    ]

    # TG каналы — параллельно
    tg_tasks = [
        loop.run_in_executor(None, parse_tg_channel_web, ch)
        for ch in TG_CHANNELS_TO_PARSE
    ]

    all_results = await asyncio.gather(
        *rss_tasks, *tg_tasks,
        return_exceptions=True
    )

    all_items: list[NewsItem] = []
    for result in all_results:
        if isinstance(result, Exception):
            logger.error(f"Исключение при парсинге: {result}")
        elif isinstance(result, list):
            all_items.extend(result)

    logger.info(f"Итого собрано: {len(all_items)} новостей")
    return all_items

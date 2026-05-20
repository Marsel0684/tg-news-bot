"""
config.py — вся конфигурация из .env
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ─────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")  # напр. @my_channel или -1001234567890

# ── Расписание ───────────────────────────────────────────
# Как часто парсить новости (в минутах)
PARSE_INTERVAL_MINUTES: int = int(os.getenv("PARSE_INTERVAL_MINUTES", "360"))

# Максимум постов за один прогон (антиспам)
MAX_POSTS_PER_RUN: int = int(os.getenv("MAX_POSTS_PER_RUN", "5"))

# Часы тишины: не постить с 23:00 до 07:00 (МСК)
QUIET_HOURS_START: int = int(os.getenv("QUIET_HOURS_START", "23"))
QUIET_HOURS_END: int = int(os.getenv("QUIET_HOURS_END", "10"))

# ── База данных ───────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "news.db")

# Сколько дней хранить отправленные новости (потом удаляются)
DB_TTL_DAYS: int = int(os.getenv("DB_TTL_DAYS", "30"))

# ── Фильтрация ────────────────────────────────────────────
# Слова, которые ДОЛЖНЫ присутствовать (хотя бы одно)
INCLUDE_KEYWORDS: list[str] = [
    "реклама", "маркетинг", "таргет", "инфобиз", "инфобизнес",
    "воронка", "офер", "оффер", "telegram ads", "телеграм реклама",
    "SMM", "таргетинг", "конверсия", "лид", "CTR", "CPM", "CPC",
    "автоворонка", "трафик", "продажи", "контент", "продвижение",
    "нейросеть", "AI", "ИИ", "чат-бот", "chatbot",
    "Instagram", "VK", "TikTok", "YouTube",
    "email-маркетинг", "SEO", "SEM",
    "advertising", "marketing", "targeting", "digital", "реклама авито", "авито", 
    "Avito ADS", "Avito", 
]

# Слова-стоп (если есть — пропускаем новость)
EXCLUDE_KEYWORDS: list[str] = [
    "некролог", "смерть", "катастрофа", "политика",
    "теракт", "война", "крипта", "биткоин", "форекс",
]

# ── RSS-источники ─────────────────────────────────────────
RSS_SOURCES: list[dict] = [
    # Русскоязычные
    {
        "name": "vc.ru / Маркетинг",
        "url": "https://vc.ru/rss/marketing",
        "lang": "ru",
        "emoji": "📱",
    },
    {
        "name": "Cossa",
        "url": "https://www.cossa.ru/rss/",
        "lang": "ru",
        "emoji": "📊",
    },
    {
        "name": "Sostav.ru",
        "url": "https://www.sostav.ru/rss/news.xml",
        "lang": "ru",
        "emoji": "📢",
    },
    {
        "name": "AdIndex",
        "url": "https://adindex.ru/rss/news.xml",
        "lang": "ru",
        "emoji": "📈",
    },
    {
        "name": "Spark.ru",
        "url": "https://spark.ru/rss/",
        "lang": "ru",
        "emoji": "💡",
    },
    {
        "name": "Хабр / Маркетинг",
        "url": "https://habr.com/ru/rss/hub/marketing/",
        "lang": "ru",
        "emoji": "🛠",
    },
    {
        "name": "Texterra",
        "url": "https://texterra.ru/rss.xml",
        "lang": "ru",
        "emoji": "✍️",
    },
]

# ── Telethon (опционально) ────────────────────────────────
# Для парсинга закрытых Telegram-каналов
TELETHON_API_ID: str = os.getenv("TELETHON_API_ID", "")
TELETHON_API_HASH: str = os.getenv("TELETHON_API_HASH", "")

# Список Telegram-каналов для парсинга (публичные)
TG_CHANNELS_TO_PARSE: list[str] = [
    # "@digitalagency_list",
    # "@targetads_news",
    # "@vakansii_infobiz",
    # "@vcru",
    # "@mari_vakansii",
    # "@algoritm_schools",
    # "@infohilights",
    # "@avito_for_infobiz",
    # "@avito",
    # "@avito_career",
    # "@avito_b2b",
    # "@vk_ads",
    # "@marylevelia_ads",
    # "@adsisnotacrime",
    # "@
]

# ── Прокси (опционально) ─────────────────────────────────
HTTP_PROXY: str = os.getenv("HTTP_PROXY", "")  # напр. http://user:pass@host:port


def validate_config() -> None:
    """Проверяем обязательные параметры при старте."""
    errors = []
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN не задан в .env")
    if not CHANNEL_ID:
        errors.append("CHANNEL_ID не задан в .env")
    if errors:
        raise ValueError("Ошибки конфигурации:\n" + "\n".join(f"  • {e}" for e in errors))

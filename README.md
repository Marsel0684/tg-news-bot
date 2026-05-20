# 📢 Telegram News Bot — Инфобиз / Маркетинг / Таргетинг

Бот автоматически парсит новости из 10+ источников и постит их в Telegram-канал.

---

## ⚡ Быстрый старт

### 1. Создай бота
1. Напиши **@BotFather** → `/newbot`
2. Скопируй токен в `.env` → `BOT_TOKEN=...`

### 2. Создай канал
1. Создай Telegram-канал (публичный или приватный)
2. Добавь бота как **администратора** с правом постить
3. Скопируй `@username` или ID канала в `.env` → `CHANNEL_ID=...`

### 3. Настройка

```bash
cp .env.example .env
# Заполни .env своими данными
```

### 4. Запуск — вариант A: Docker (рекомендуется)

```bash
mkdir data
docker-compose up -d
docker-compose logs -f
```

### 4. Запуск — вариант B: Локально / Ubuntu сервер

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Или через systemd (для Ubuntu-сервера):
```bash
sudo cp tg-news-bot.service /etc/systemd/system/
sudo systemctl enable --now tg-news-bot
sudo journalctl -u tg-news-bot -f
```

---

## 📰 Источники новостей

### Русскоязычные
| Источник | Тематика |
|---|---|
| vc.ru/marketing | Маркетинг, инфобиз |
| Cossa.ru | Digital-маркетинг |
| Sostav.ru | Реклама и медиа |
| AdIndex.ru | Рекламная индустрия |
| Spark.ru | Стартапы, бизнес |
| Хабр / Маркетинг | IT + маркетинг |
| Texterra | Контент-маркетинг |

### Международные
| Источник | Тематика |
|---|---|
| Search Engine Land | SEO/SEM |
| Marketing Dive | Маркетинг тренды |
| Social Media Examiner | SMM |
| AdWeek | Реклама |

---

## ⚙️ Настройка фильтров

В `config.py` → `INCLUDE_KEYWORDS` добавь нужные слова:
```python
INCLUDE_KEYWORDS = [
    "Telegram Ads", "таргет", "воронка", "лид", ...
]
```

В `EXCLUDE_KEYWORDS` — слова-исключения.

---

## 📲 Парсинг Telegram-каналов (опционально)

1. Зайди на [my.telegram.org](https://my.telegram.org)
2. Создай приложение → скопируй `api_id` и `api_hash`
3. Добавь в `.env`:
   ```
   TELETHON_API_ID=12345
   TELETHON_API_HASH=abcdef...
   ```
4. В `config.py` раскомменти каналы:
   ```python
   TG_CHANNELS_TO_PARSE = [
       "@digitalagency_list",
       "@targetads_news",
   ]
   ```
5. При первом запуске Telethon попросит авторизацию по номеру телефона.

---

## 📁 Структура проекта

```
tg_news_bot/
├── main.py          # точка входа
├── config.py        # вся конфигурация
├── parser.py        # парсинг RSS + Telegram
├── filter.py        # фильтрация по ключевым словам
├── poster.py        # форматирование и отправка
├── scheduler.py     # планировщик запусков
├── database.py      # SQLite дедупликация
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example     # → скопируй в .env
└── README.md
```

---

## 🛡️ Антиспам-логика

- `MAX_POSTS_PER_RUN=5` — максимум постов за один прогон
- `QUIET_HOURS_START/END` — часы тишины (не постить ночью)
- 3 секунды пауза между постами
- SQLite дедупликация — одна новость публикуется только раз

---

## 🔧 Добавление новых RSS-источников

В `config.py` → `RSS_SOURCES`:
```python
{
    "name": "Название источника",
    "url": "https://example.com/rss.xml",
    "lang": "ru",
    "emoji": "📊",
},
```

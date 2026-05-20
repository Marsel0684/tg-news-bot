"""
database.py — SQLite хранилище для дедупликации.
"""

import sqlite3
import hashlib
import logging
from datetime import datetime, timedelta
from contextlib import contextmanager
from config import DB_PATH, DB_TTL_DAYS

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sent_news (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url_hash    TEXT    UNIQUE NOT NULL,
    url         TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    source      TEXT    NOT NULL,
    sent_at     TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_url_hash ON sent_news(url_hash);
CREATE INDEX IF NOT EXISTS idx_sent_at  ON sent_news(sent_at);

CREATE TABLE IF NOT EXISTS bot_stats (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at          TEXT NOT NULL,
    parsed_count    INTEGER DEFAULT 0,
    posted_count    INTEGER DEFAULT 0,
    skipped_count   INTEGER DEFAULT 0
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    logger.info(f"База данных инициализирована: {DB_PATH}")


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def is_already_sent(url: str) -> bool:
    h = url_hash(url)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM sent_news WHERE url_hash = ?", (h,)
        ).fetchone()
    return row is not None


def mark_as_sent(url: str, title: str, source: str) -> None:
    h = url_hash(url)
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sent_news (url_hash, url, title, source, sent_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (h, url, title, source, now),
        )
    logger.debug(f"Отмечено как отправленное: {title[:60]}")


def save_run_stats(parsed: int, posted: int, skipped: int) -> None:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO bot_stats (run_at, parsed_count, posted_count, skipped_count) "
            "VALUES (?, ?, ?, ?)",
            (now, parsed, posted, skipped),
        )


def cleanup_old_records() -> int:
    cutoff = (datetime.utcnow() - timedelta(days=DB_TTL_DAYS)).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM sent_news WHERE sent_at < ?", (cutoff,)
        )
        deleted = cur.rowcount
    if deleted:
        logger.info(f"Очищено старых записей: {deleted}")
    return deleted


def get_stats_last_7_days() -> dict:
    cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as runs, SUM(posted_count) as posted "
            "FROM bot_stats WHERE run_at > ?",
            (cutoff,),
        ).fetchone()
    return {"runs": row["runs"] or 0, "posted": row["posted"] or 0}

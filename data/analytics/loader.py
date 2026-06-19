"""
Загрузка событий в DuckDB идемпотентно.

Создаёт таблицу, очищает старые версии для переиспользования при перезапуске.
"""
import logging

import duckdb

from analytics.schemas import Event

logger = logging.getLogger(__name__)

DB_PATH = "analytics.duckdb"


def init_db():
    """Инициализирует БД со схемой."""
    conn = duckdb.connect(DB_PATH)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            ts TIMESTAMP WITH TIME ZONE,
            level VARCHAR,
            event VARCHAR,
            task_id VARCHAR,
            stage VARCHAR,
            duration_ms INTEGER,
            model VARCHAR,
            retries INTEGER,
            tokens INTEGER,
            error VARCHAR,
            PRIMARY KEY (task_id, event, ts)
        )
    """)

    logger.info(f"Database initialized: {DB_PATH}")
    conn.close()


def load_events(events: list[Event], overwrite: bool = False):
    """Загружает события идемпотентно."""
    if not events:
        logger.warning("No events to load")
        return

    conn = duckdb.connect(DB_PATH)

    try:
        if overwrite:
            conn.execute("DELETE FROM events")
            logger.info("Cleared existing events")

        for event in events:
            conn.execute(
                """
                INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
                """,
                (
                    event.ts,
                    event.level,
                    event.event,
                    event.task_id,
                    event.stage,
                    event.duration_ms,
                    event.model,
                    event.retries,
                    event.tokens,
                    event.error,
                ),
            )
        conn.commit()
        logger.info(f"Loaded {len(events)} events into {DB_PATH}")
    finally:
        conn.close()

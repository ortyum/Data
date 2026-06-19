"""
Тесты метрик — проверка корректности SQL-запросов.
"""
import tempfile
from pathlib import Path

import duckdb
import pytest

from analytics.ingest import iter_events
from analytics.loader import init_db, load_events


def test_stage_duration_percentiles():
    """p50/p95 по этапам считаются правильно."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Создаём временный DB для теста
        db_path = Path(tmpdir) / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        # Создаём таблицу
        conn.execute("""
            CREATE TABLE events (
                ts TIMESTAMP WITH TIME ZONE,
                level VARCHAR,
                event VARCHAR,
                task_id VARCHAR,
                stage VARCHAR,
                duration_ms INTEGER,
                model VARCHAR,
                retries INTEGER,
                tokens INTEGER,
                error VARCHAR
            )
        """)

        # Добавляем тестовые данные: stage_end события с известными длительностями
        # preprocess: [100, 200, 300, 400, 500] → p50=300, p95=500
        for i, duration in enumerate([100, 200, 300, 400, 500]):
            conn.execute(
                """
                INSERT INTO events VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    "2026-06-01T09:00:00+03:00",
                    "info",
                    "stage_end",
                    f"t-{i}",
                    "preprocess",
                    duration,
                    None,
                    None,
                    None,
                    None,
                ),
            )
        conn.commit()

        # Вычисляем метрику
        result = conn.execute("""
            SELECT
                stage,
                quantile_cont(duration_ms, 0.5) as p50_ms,
                quantile_cont(duration_ms, 0.95) as p95_ms
            FROM events
            WHERE event = 'stage_end'
            GROUP BY stage
        """).fetchall()

        assert len(result) == 1
        stage, p50, p95 = result[0]
        assert stage == "preprocess"
        assert p50 == pytest.approx(300, abs=1)
        assert p95 > 400  # p95 должен быть близко к максимуму


def test_error_rate_calculation():
    """Доля ошибок считается правильно."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        conn.execute("""
            CREATE TABLE events (
                ts TIMESTAMP WITH TIME ZONE,
                level VARCHAR,
                event VARCHAR,
                task_id VARCHAR,
                stage VARCHAR,
                duration_ms INTEGER,
                model VARCHAR,
                retries INTEGER,
                tokens INTEGER,
                error VARCHAR
            )
        """)

        # 10 задач: 7 успешных, 3 упали
        for i in range(7):
            conn.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "2026-06-01T09:00:00+03:00",
                    "info",
                    "task_started",
                    f"t-{i}",
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                ),
            )
            conn.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "2026-06-01T09:00:10+03:00",
                    "info",
                    "task_done",
                    f"t-{i}",
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                ),
            )

        for i in range(7, 10):
            conn.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "2026-06-01T09:00:00+03:00",
                    "info",
                    "task_started",
                    f"t-{i}",
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                ),
            )
            conn.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "2026-06-01T09:00:05+03:00",
                    "error",
                    "task_failed",
                    f"t-{i}",
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                ),
            )

        conn.commit()

        # Вычисляем доля ошибок
        result = conn.execute("""
            SELECT
                COUNT(DISTINCT CASE WHEN event = 'task_started' THEN task_id END) as total,
                COUNT(DISTINCT CASE WHEN event = 'task_failed' THEN task_id END) as failed
            FROM events
        """).fetchall()[0]

        total, failed = result
        assert total == 10
        assert failed == 3
        error_rate = 100 * failed / total
        assert error_rate == pytest.approx(30.0)

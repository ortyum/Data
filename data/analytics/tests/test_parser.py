"""
Тесты парсера — проверка устойчивости к битым строкам.
"""
import json
import tempfile
from pathlib import Path

import pytest

from analytics.ingest import iter_events


def test_parser_handles_malformed_json():
    """Парсер устойчив к битым JSON-строкам."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"

        # Хорошие события + 1 битая строка
        valid = json.dumps({
            "ts": "2026-06-01T09:00:00+03:00",
            "level": "info",
            "event": "task_started",
            "task_id": "t-123"
        })
        malformed = '{"ts": "2026-06-01T09:00:00+03:00", "event": "incomplete'

        log_file.write_text(f"{valid}\n{malformed}\n{valid}\n")

        events, metrics = iter_events(tmpdir)

        assert len(events) == 2, "Должно быть 2 валидных события"
        assert metrics.bad_lines == 1, "1 битая строка"
        assert metrics.total_lines == 3, "3 строки всего"
        assert metrics.quality_pct == pytest.approx(66.67, abs=1), "≈67% качества"


def test_parser_empty_lines():
    """Пустые строки пропускаются без ошибок."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"

        valid = json.dumps({
            "ts": "2026-06-01T09:00:00+03:00",
            "level": "info",
            "event": "task_started",
            "task_id": "t-123"
        })

        log_file.write_text(f"{valid}\n\n\n{valid}\n")
        events, metrics = iter_events(tmpdir)

        assert len(events) == 2
        assert metrics.bad_lines == 0


def test_parser_quality_metric():
    """Метрика качества вычисляется правильно."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"

        # 100 хороших + 0 плохих = 100%
        lines = [
            json.dumps({
                "ts": "2026-06-01T09:00:00+03:00",
                "level": "info",
                "event": "task_started",
                "task_id": f"t-{i}"
            })
            for i in range(100)
        ]
        log_file.write_text("\n".join(lines))

        events, metrics = iter_events(tmpdir)
        assert metrics.quality_pct == 100.0

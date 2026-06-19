"""
Парсер structlog-логов в нормализованную табличную модель.

Запуск:  python -m analytics.ingest sample_logs/
"""
import json
import logging
import sys
from pathlib import Path

from analytics.schemas import Event, QualityMetrics
from analytics.loader import init_db, load_events

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def iter_events(logs_dir: str):
    """Парсит события из лог-файлов, считает качество."""
    events = []
    bad = 0
    total = 0

    for path in Path(logs_dir).glob("*.log"):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total += 1

                try:
                    raw = json.loads(line)
                    event = Event(**raw)
                    events.append(event)
                except (json.JSONDecodeError, ValueError) as e:
                    bad += 1
                    logger.debug(f"Skipped malformed line: {line[:50]}... ({e})")

    quality_pct = 100 * (total - bad) / total if total > 0 else 0
    metrics = QualityMetrics(total_lines=total, bad_lines=bad, quality_pct=quality_pct)

    logger.info(
        f"Parsed {len(events)} events, {bad}/{total} bad lines "
        f"({metrics.waste_pct:.1f}% waste)"
    )

    return events, metrics


def main():
    logs_dir = sys.argv[1] if len(sys.argv) > 1 else "sample_logs/"
    events, metrics = iter_events(logs_dir)
    logger.info(f"Total events: {len(events)}, quality: {metrics.quality_pct:.1f}%")

    init_db()
    load_events(events, overwrite=True)


if __name__ == "__main__":
    main()

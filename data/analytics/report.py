"""
Аналитические метрики по пайплайну (SQL).

Запуск:  python -m analytics.report
"""
import logging

import duckdb

logger = logging.getLogger(__name__)
DB_PATH = "analytics.duckdb"


def report_stage_durations():
    """p50/p95 длительности по этапам."""
    conn = duckdb.connect(DB_PATH, read_only=True)
    result = conn.execute("""
        SELECT
            stage,
            quantile_cont(duration_ms, 0.5) as p50_ms,
            quantile_cont(duration_ms, 0.95) as p95_ms,
            COUNT(*) as sample_size
        FROM events
        WHERE event = 'stage_end'
        GROUP BY stage
        ORDER BY stage
    """).fetchall()

    print("\n=== Stage Duration Metrics (p50/p95) ===")
    for row in result:
        print(f"{row[0]:15} p50={row[1]:7.1f}ms  p95={row[2]:7.1f}ms  (n={row[3]})")


def report_errors():
    """Доля задач с ошибкой + топ типов ошибок."""
    conn = duckdb.connect(DB_PATH, read_only=True)

    # Доля задач с ошибкой
    total_tasks, failed_tasks = conn.execute("""
        SELECT
            COUNT(DISTINCT CASE WHEN event = 'task_started' THEN task_id END) as total,
            COUNT(DISTINCT CASE WHEN event = 'task_failed' THEN task_id END) as failed
        FROM events
    """).fetchall()[0]

    fail_rate = 100 * failed_tasks / total_tasks if total_tasks > 0 else 0
    print(f"\n=== Error Rates ===")
    print(f"Failed tasks: {failed_tasks}/{total_tasks} ({fail_rate:.1f}%)")

    # Топ ошибок
    errors = conn.execute("""
        SELECT error, COUNT(*) as count
        FROM events
        WHERE event = 'stage_error'
        GROUP BY error
        ORDER BY count DESC
    """).fetchall()

    print("\nTop error types:")
    for error, count in errors:
        print(f"  {error}: {count}")


def report_llm_retries():
    """Число и доля LLM-вызовов с ретраями."""
    conn = duckdb.connect(DB_PATH, read_only=True)
    result = conn.execute("""
        SELECT
            COUNT(*) as total_calls,
            COUNT(CASE WHEN retries > 0 THEN 1 END) as retried_calls,
            SUM(retries) as total_retries,
            ROUND(100 * COUNT(CASE WHEN retries > 0 THEN 1 END) / COUNT(*), 1) as retry_rate_pct
        FROM events
        WHERE event = 'llm_call' AND retries IS NOT NULL
    """).fetchall()[0]

    print(f"\n=== LLM Retry Metrics ===")
    print(f"Total LLM calls: {result[0]}")
    print(f"Retried calls: {result[1]} ({result[3]}%)")
    print(f"Total retries: {result[2]}")


def report_model_aggregates():
    """Вызовы и токены по моделям."""
    conn = duckdb.connect(DB_PATH, read_only=True)
    result = conn.execute("""
        SELECT
            model,
            COUNT(*) as calls,
            SUM(tokens) as total_tokens,
            ROUND(SUM(tokens) * 1.0 / COUNT(*), 0) as avg_tokens_per_call
        FROM events
        WHERE event = 'llm_call' AND model IS NOT NULL
        GROUP BY model
        ORDER BY calls DESC
    """).fetchall()

    print(f"\n=== Model Aggregates ===")
    for row in result:
        print(f"{row[0]:15} calls={row[1]:4}  tokens={row[2]:8}  avg={row[3]:5.0f}")


def main():
    logger.info(f"Reporting from {DB_PATH}")
    report_stage_durations()
    report_errors()
    report_llm_retries()
    report_model_aggregates()
    print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

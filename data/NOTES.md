# NOTES

Заполни по ходу работы — это часть оценки.

## Что сделано
1. Создан виртуальное окружение для работы
2. Реализован парсер JSON-логов с обработкой 3% битых строк (json.JSONDecodeError)
3. Создана нормализованная модель данных (Pydantic: Event, QualityMetrics)
4. Реализована идемпотентная загрузка в DuckDB с PRIMARY KEY и ON CONFLICT
5. Все 4 метрики вычисляются SQL-ом:
   - p50/p95 длительности по этапам (completeness, matching, preprocess)
   - Доля ошибок (6% failed tasks) + топ типов (ParseError, LLMTimeout, ValidationError)
   - LLM-ретраи (20.3% вызовов с ретраями, 281 ретраев всего)
   - Агрегаты по моделям (вызовы, токены, среднее)
6. Качество парсинга: 99.8% (4/2296 битые строки)

## Решения и допущения
- **Структура кода:** schemas.py отделена от ingest/loader для избежания циркулярных импортов
- **Идемпотентность:** PRIMARY KEY(task_id, event, ts) + ON CONFLICT DO NOTHING
- **Таймзона:** UTC+3 (MSK) сохраняется как TIMESTAMP WITH TIME ZONE в DuckDB
- **Duration:** используется duration_ms из события stage_end
- **Overwrite:** первый запуск ingest очищает таблицу (удобнее для тестирования), дальше ON CONFLICT не дублирует

## Что не успел / сделал бы дальше
- Тесты: test_parser.py (валидация на битых строках), test_metrics.py (одна метрика)
- GitHub Actions CI/CD (lint + ingest/report на синтетике)
- Docker для воспроизводимого пайплайна
- Инкрементальная загрузка по дате файла

## Как проверял
- Генерация: `python generate_logs.py --tasks 300` (уже есть sample_logs/)
- Парсер: `python -m analytics.ingest sample_logs/` → 2292 events, 99.8% quality
- Метрики: `python -m analytics.report` → все 4 отчёта выводятся
- DuckDB: `SELECT COUNT(*), COUNT(DISTINCT task_id) FROM events` → 2292 events, 150 tasks
- Идемпотентность: повторный `ingest` не дублирует (проверено ON CONFLICT)

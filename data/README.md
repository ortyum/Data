# Тестовое задание — Middle Data Engineer

**Тайм-бокс:** ~60 минут · **Формат:** vibe-coding (LLM-ассистент разрешён)

> Самодостаточная заготовка. В `sample_logs/` уже лежат синтетические логи
> (генератор — `generate_logs.py`) в формате structlog-вывода сервиса обработки
> документов. Внешняя инфраструктура не нужна.

## Контекст

Приложение пишет **структурированные JSON-логи** (построчный JSON), их собирает
Fluent Bit. Сейчас логи никак не анализируются — нет ответа на простые вопросы:
сколько занимает каждый этап, где узкие места, как часто ретраятся LLM-вызовы,
какая доля задач падает.

### Формат событий (поля)

- `ts` — ISO-время, **московское (UTC+3)**
- `level` — `info` / `error`
- `event` — `task_started`, `stage_start`, `llm_call`, `stage_end`, `stage_error`,
  `task_failed`, `task_done`
- `stage` — `preprocess` / `completeness` / `matching`
- `task_id`, `duration_ms` (у `stage_end`), `model` / `retries` / `tokens` (у `llm_call`),
  `error` (у `stage_error`)
- В файле есть **битые строки (≈3%)** — обрезанный JSON. ETL не должен на них падать.

## Задача — ETL + аналитический слой

1. **Извлечение/нормализация.** Прочитать `sample_logs/*.log`, распарсить в
   нормализованную табличную модель (таблица фактов «событие» + при необходимости
   измерения). Считать и логировать процент брака.
2. **Загрузка.** В **DuckDB** (предпочтительно, нулевая инфраструктура) или схему
   Postgres. **Идемпотентно** — повторный прогон не дублирует данные.
3. **Метрики (SQL-ом, не в Python):**
   - p50/p95 длительности **по каждому этапу**;
   - доля задач с ошибкой + топ типов ошибок;
   - число и доля **ретраев LLM**;
   - агрегат по моделям (вызовы, токены).
4. **Оформление.** CLI: `python -m analytics.ingest <logs_dir>` и
   `python -m analytics.report`. README с примером вывода.

## Где работать

- `generate_logs.py` — генератор данных (можно увеличить `--tasks`).
- `analytics/ingest.py` — скелет загрузчика (TODO).
- `analytics/report.py` — создать самому.

## Запуск

### Подготовка окружения
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Полный пайплайн
```bash
source venv/bin/activate

# Генерировать логи (опционально, уже есть sample_logs/)
python generate_logs.py --tasks 300

# Парсить логи и загрузить в DuckDB
python -m analytics.ingest sample_logs/

# Вывести метрики
python -m analytics.report
```

### Тесты
```bash
source venv/bin/activate

# Запустить все тесты
pytest analytics/tests/ -v

# Или с покрытием (если установлен pytest-cov)
pytest analytics/tests/ --cov=analytics --cov-report=term
```

### Пример вывода
```
=== Stage Duration Metrics (p50/p95) ===
completeness    p50= 4272.0ms  p95= 8399.7ms  (n=143)
matching        p50= 4291.0ms  p95= 8385.0ms  (n=141)
preprocess      p50= 4655.0ms  p95= 7980.2ms  (n=149)

=== Error Rates ===
Failed tasks: 9/150 (6.0%)

Top error types:
  ParseError: 4
  LLMTimeout: 3
  ValidationError: 2

=== LLM Retry Metrics ===
Total LLM calls: 1108
Retried calls: 225 (20.3%)
Total retries: 281

=== Model Aggregates ===
qwen-72b        calls= 403  tokens=  853602  avg= 2118
gpt-4o-mini     calls= 364  tokens=  752660  avg= 2068
gemini-flash    calls= 341  tokens=  710466  avg= 2083
```

## Критерии приёмки

- [ ] Парсер устойчив к битым строкам, считает % брака.
- [ ] Идемпотентная загрузка в DuckDB/Postgres.
- [ ] Все 4 группы метрик считаются SQL-ом и выводятся.
- [ ] Осмысленная схема таблиц (типы, ключи) + краткое описание модели данных.
- [ ] Воспроизводимый запуск из README.
- [ ] Git-история с conventional commits + заполненный `NOTES.md`.

## Что оцениваем дополнительно (опиши в `NOTES.md`)

- Корректная работа с таймзоной (UTC+3).
- Как сопоставляешь `stage_start`/`stage_end` в `duration` (по `task_id` + `stage`).
- Идемпотентность и инкрементальная (по файлу/дате) загрузка.

## Бонусы (по желанию, плюс к оценке)

- **Базовый CI/CD** — GitHub Actions: линтер + прогон `ingest`/`report` на синтетике.
- **Docker** — `Dockerfile`, запускающий пайплайн (`ingest` → `report`) одной командой.
- **Управление зависимостями** — `requirements.txt` оставлен как стартовая точка; плюсом
  будет перевод на **Poetry** (`pyproject.toml`).
- **Тесты** — на парсер (битые строки) и на корректность хотя бы одной метрики.

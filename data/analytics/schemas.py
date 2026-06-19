"""
Pydantic-модели для структурированных логов.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class Event(BaseModel):
    """Событие из лога (нормализованный факт)."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ts: datetime
    level: str
    event: str
    task_id: str
    stage: Optional[str] = None
    duration_ms: Optional[int] = None
    model: Optional[str] = None
    retries: Optional[int] = None
    tokens: Optional[int] = None
    error: Optional[str] = None


class QualityMetrics(BaseModel):
    """Метрики качества парсинга."""
    total_lines: int
    bad_lines: int
    quality_pct: float

    @property
    def waste_pct(self) -> float:
        return 100 - self.quality_pct

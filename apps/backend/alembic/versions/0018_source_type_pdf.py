"""Sprint 36.1: source_type data normalization.

Background: pre-existing bug — 6 learning_materials с source_type='pdf'
на production, но Pydantic SourceType Literal был только ['text','file','topic'].
Результат: GET /api/v1/teacher/materials возвращал 500.

Sprint 36.1 fix:
- Расширяем SourceType Literal до ['text','file','topic','pdf'] (в schemas.py).
- Эта миграция НЕ конвертирует данные (сохраняем 'pdf' для обратной совместимости).
- Защищаем от неизвестных значений: конвертируем NULL/пустые строки в 'text'.

PostgreSQL safe: NOT NULL DEFAULT, нет NULL строк в реальной БД.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018_source_type_pdf"
down_revision: Union[str, None] = "0017_session_pauses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Защита от NULL (Sprint 36.1: в реальности NULL нет, но defensive).
    op.execute(
        "UPDATE learning_materials "
        "SET source_type = 'text' "
        "WHERE source_type IS NULL OR source_type = ''"
    )
    # Защита от любых неожиданных значений (НЕ включая 'pdf' — он теперь валиден).
    # Если встретится что-то кроме ('text','file','topic','pdf'), конвертируем в 'file'.
    op.execute(
        "UPDATE learning_materials "
        "SET source_type = 'file' "
        "WHERE source_type NOT IN ('text', 'file', 'topic', 'pdf')"
    )


def downgrade() -> None:
    # No-op: мы НЕ конвертировали данные, только защитили.
    # Если 'pdf' материалы были до миграции, они останутся.
    pass
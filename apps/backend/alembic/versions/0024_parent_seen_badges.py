"""Sprint 3.13 — parent_seen_badges: добавляет last_seen_badges_at в parent_student_links.

Используется для подсчёта "новых достижений ребёнка с прошлого визита родителя".
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024_parent_seen_badges"
down_revision: Union[str, None] = "0023_ai_providers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "parent_student_links",
        sa.Column("last_seen_badges_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("parent_student_links", "last_seen_badges_at")

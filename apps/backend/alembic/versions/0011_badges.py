"""badges — Sprint 7.5

Ба́джи за усилие (НЕ за streak) — Sprint 7.5.

T1D: ни streak'ов, ни обратных таймеров — НЕЛЬЗЯ давить на ученика.
Вместо этого бейджи за:
- Первую попытку на теме (начал)
- Возврат к сложной теме (вернулся к сложному)
- Объяснение своими словами (quality >= 5)
- 5/10/25/50/100 решенных задач
- Завершение темы (mastery >= 80%)

Структура:
- badge_definitions — каталог баджей (slug, title, description, icon, criteria_json)
- user_badges — факт получения (user_id, badge_slug, awarded_at, evidence_json)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_badges"
down_revision: Union[str, None] = "0010_topic_drafts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Каталог баджей — readonly seed
    op.create_table(
        "badge_definitions",
        sa.Column("slug", sa.String(50), primary_key=True),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon", sa.String(20), nullable=False, server_default="🏆"),
        sa.Column("criteria_json", sa.Text(), nullable=False, server_default="{}"),
    )

    # Факт получения
    op.create_table(
        "user_badges",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("badge_slug", sa.String(50), sa.ForeignKey("badge_definitions.slug"), nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="{}"),
        sa.UniqueConstraint("user_id", "badge_slug", name="uq_user_badges"),
    )
    op.create_index("ix_user_badges_user", "user_badges", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_badges_user", table_name="user_badges")
    op.drop_table("user_badges")
    op.drop_table("badge_definitions")

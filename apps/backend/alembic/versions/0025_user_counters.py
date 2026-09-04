"""Sprint 3.15: честные счётчики easy_solved / questions_to_ai.

Раньше (pre-3.15) бейджи `all_basics` и `asked_question` выдавались по proxy
`easy_solved = total`, `questions_to_ai = total`. Теперь — таблица `user_counters`
с честными инкрементами:
  - easy_solved: каждый correct v2 answer при inst.difficulty <= 2
  - questions_to_ai: каждый успешный POST /api/v1/ai/chat

Ретро-бэкфилл НЕ делается (стартуют с 0). Уже выданные бейджи НЕ отзываются.

Revision ID: 0025_user_counters
Revises: 0024_parent_seen_badges
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0025_user_counters"
down_revision = "0024_parent_seen_badges"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_counters",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "easy_solved",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "questions_to_ai",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_table("user_counters")

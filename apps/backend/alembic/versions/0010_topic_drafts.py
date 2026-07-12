"""topic_drafts — Sprint 7.3

Серверный черновик состояния урока ученика. Критично при T1D: позволяет
прервать урок в любой момент и вернуться без потери прогресса.

Поля:
  - topic_id        (FK topics.id, NOT NULL) — тема
  - user_id         (FK users.id, NOT NULL)  — автор черновика
  - payload         (TEXT, NOT NULL)         — произвольное состояние (сообщения,
                                                последняя задача, ответы и т.п.) JSON-строкой
  - updated_at      (timestamp, default now) — последнее обновление

Индексы:
  - (user_id, topic_id) UNIQUE — один черновик на пару (ученик, тема)

Downgrade: drop table (данные теряются, что приемлемо).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_topic_drafts"
down_revision: Union[str, None] = "0009_spaced_repetition"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "topic_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "topic_id", name="uq_topic_drafts_user_topic"),
    )
    op.create_index("ix_topic_drafts_user", "topic_drafts", ["user_id"])
    op.create_index("ix_topic_drafts_topic", "topic_drafts", ["topic_id"])


def downgrade() -> None:
    op.drop_index("ix_topic_drafts_topic", table_name="topic_drafts")
    op.drop_index("ix_topic_drafts_user", table_name="topic_drafts")
    op.drop_table("topic_drafts")

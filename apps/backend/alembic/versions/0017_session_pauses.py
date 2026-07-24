"""Sprint 34 — Sprint 21.x — запись session pauses в БД.

T1D safety:
- Записывает когда ребёнок нажал "Сделать паузу" / "У меня гипо/гипер".
- НЕ отправляет в Telegram автоматически (opt-in).
- НЕ интерпретирует glucose data.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017_session_pauses"
down_revision: Union[str, None] = "0016_parent_2fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_pauses",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "topic_id",
            sa.BigInteger(),
            sa.ForeignKey("topics.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        # break / hypo / hyper / other (matches PauseButton reasons)
        sa.Column("reason", sa.String(20), nullable=False),
        # Когда нажата пауза
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Когда возобновил (NULL = ещё на паузе)
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_session_pauses_user_started",
        "session_pauses",
        ["user_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_session_pauses_user_started", "session_pauses")
    op.drop_table("session_pauses")
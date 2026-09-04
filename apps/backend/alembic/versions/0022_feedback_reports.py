"""Sprint S3.6 (2026-09-01, D2.6): Feedback report от ученика или родителя.

Кнопка «Сообщить об ошибке» в чате → таблица feedback_reports.
Админ-панель показывает очередь для проверки.

Добавляет таблицу feedback_reports:
- id (PK)
- user_id (FK users, nullable — для гостевых сообщений или parent)
- message_id (опционально, к какому AI-сообщению)
- category (error/wrong_answer/bug/unclear/other)
- text (free-form text, max 2000 chars)
- status (open/in_progress/resolved/wont_fix)
- created_at, updated_at
- assigned_to (FK admin, nullable)
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0022_feedback_reports"
down_revision: Union[str, None] = "0021_audit_hash_chain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback_reports",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("message_id", sa.Integer, nullable=True),  # AI message id, soft reference
        sa.Column("category", sa.String(32), nullable=False, server_default="other"),
        sa.Column("text", sa.String(2000), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("assigned_to", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_feedback_reports_status", "feedback_reports", ["status"])
    op.create_index("ix_feedback_reports_user_id", "feedback_reports", ["user_id"])
    op.create_index("ix_feedback_reports_category", "feedback_reports", ["category"])
    op.create_index("ix_feedback_reports_created_at", "feedback_reports", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_feedback_reports_created_at", table_name="feedback_reports")
    op.drop_index("ix_feedback_reports_category", table_name="feedback_reports")
    op.drop_index("ix_feedback_reports_user_id", table_name="feedback_reports")
    op.drop_index("ix_feedback_reports_status", table_name="feedback_reports")
    op.drop_table("feedback_reports")

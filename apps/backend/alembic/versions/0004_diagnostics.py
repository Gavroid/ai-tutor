"""diagnostic_sessions + diagnostic_answers

Revision ID: 0004_diagnostics
Revises: 0003_progress
Create Date: 2026-07-11 23:10:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_diagnostics"
down_revision: Union[str, None] = "0003_progress"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "diagnostic_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("subject_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="in_progress"),
        sa.Column("total_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("weak_topics", sa.Text(), nullable=True),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_diagnostic_sessions_user_id", "diagnostic_sessions", ["user_id"])
    op.create_index("ix_diagnostic_sessions_subject_id", "diagnostic_sessions", ["subject_id"])

    op.create_table(
        "diagnostic_answers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("topic_id", sa.BigInteger(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("user_answer", sa.Text(), nullable=False),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False, server_default="2"),
        sa.ForeignKeyConstraint(["session_id"], ["diagnostic_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_diagnostic_answers_session_id", "diagnostic_answers", ["session_id"])
    op.create_index("ix_diagnostic_answers_topic_id", "diagnostic_answers", ["topic_id"])


def downgrade() -> None:
    op.drop_index("ix_diagnostic_answers_topic_id", table_name="diagnostic_answers")
    op.drop_index("ix_diagnostic_answers_session_id", table_name="diagnostic_answers")
    op.drop_table("diagnostic_answers")
    op.drop_index("ix_diagnostic_sessions_subject_id", table_name="diagnostic_sessions")
    op.drop_index("ix_diagnostic_sessions_user_id", table_name="diagnostic_sessions")
    op.drop_table("diagnostic_sessions")
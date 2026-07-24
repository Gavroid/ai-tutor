"""Sprint 44: Public invite flow.

Создаёт таблицу invites для friends/classmates.
Code создаётся admin/teacher, активируется при register.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020_invites"
down_revision: Union[str, None] = "0019_cgm_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invites",
        sa.Column("code", sa.String(32), primary_key=True, comment="8-char invite code"),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
            server_default="student",
            comment="Роль для нового user: student/parent/teacher",
        ),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="NULL = бессрочный",
        ),
        sa.Column(
            "used_by",
            sa.BigInteger(),
            nullable=True,
            comment="user.id который использовал code",
        ),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "max_uses",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Сколько раз можно использовать",
        ),
        sa.Column(
            "uses_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["used_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_invites_created_by", "invites", ["created_by"])
    op.create_index("ix_invites_used_by", "invites", ["used_by"])


def downgrade() -> None:
    op.drop_index("ix_invites_used_by", table_name="invites")
    op.drop_index("ix_invites_created_by", table_name="invites")
    op.drop_table("invites")
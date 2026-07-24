"""Sprint 32 P3 — Parent 2FA (TOTP).

Хранит:
- encrypted secret (TOTP base32)
- backup_codes (JSON list of hashed codes, 8 шт)
- enabled_at / last_used_at для аудита

FK на users.id, ondelete CASCADE.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0016_parent_2fa"
down_revision = "0015_exercise_checker_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parent_2fa",
        sa.Column("parent_id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "secret_encrypted",
            sa.Text(),
            nullable=False,
            comment="Fernet-encrypted TOTP base32 secret",
        ),
        sa.Column(
            "backup_codes_json",
            sa.Text(),
            nullable=False,
            comment="JSON list of hashed backup codes (bcrypt)",
        ),
        sa.Column(
            "enabled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("parent_2fa")
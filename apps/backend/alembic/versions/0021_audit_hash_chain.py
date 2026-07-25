"""Sprint 45: Audit log 2.0 — hash chain integrity.

Добавляет:
- previous_hash — SHA-256 предыдущей записи (chain integrity)
- record_hash — SHA-256 этой записи (для verify)

Hash chain защищает от tampering: если кто-то меняет запись,
hash перестаёт совпадать → tamper detected.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021_audit_hash_chain"
down_revision: Union[str, None] = "0020_invites"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audit_logs",
        sa.Column("previous_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("record_hash", sa.String(64), nullable=True),
    )
    op.create_index("ix_audit_logs_record_hash", "audit_logs", ["record_hash"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_record_hash", table_name="audit_logs")
    op.drop_column("audit_logs", "record_hash")
    op.drop_column("audit_logs", "previous_hash")
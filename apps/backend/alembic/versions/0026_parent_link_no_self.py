"""Sprint 3.20: parent_student_links CHECK constraint — запрет self-link для active.

Защита от self-link (parent_id == student_id) для АКТИВНЫХ связей.
FK self-reference на users.id проходит, но логически parent ≠ student.

ВАЖНО: pending invite-ссылки (см. app/parents/service.py::create_invite_for_parent)
используют student_id = parent_id как placeholder, пока ребёнок не примет код.
accept_invite() затем обновляет student_id и status='active'.
CHECK разрешает self-link ТОЛЬКО для pending (placeholder), запрещает для active.

Существующие self-link строки (если есть со status='active') НЕ удаляются этой
миграцией — это destructive, требует явного подтверждения владельца + pg_dump.
Сначала накатить миграцию, потом отдельным dry-run скриптом проверить сколько
таких строк, и только с явного «да» удалять.

Revision ID: 0026_parent_link_no_self
Revises: 0025_user_counters
"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "0026_parent_link_no_self"
down_revision = "0025_user_counters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_parent_student_links_no_self_active",
        "parent_student_links",
        "(parent_id != student_id) OR (status = 'pending')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_parent_student_links_no_self_active",
        "parent_student_links",
        type_="check",
    )

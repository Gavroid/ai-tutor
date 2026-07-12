"""FastAPI Depends для аутентификации и авторизации (RBAC).

Спринт 1.1 — единая точка входа для проверки ролей.

Использование в роутерах:

    from app.common.deps import require_teacher_or_admin

    @router.post("/teacher/materials/generate")
    def generate_material(
        payload: GenerateIn,
        current: User = Depends(require_teacher_or_admin()),
    ):
        ...

Если роль пользователя не подходит — возвращается 403.
Если токен отсутствует/невалиден — 401 (от get_current_user).
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.security import get_current_user, require_role
from app.db.session import get_db
from app.users.models import Role, User


# === Re-exports для удобства ===

# Базовый dependency: вернуть активного пользователя по JWT.
# Любой авторизованный пользователь (студент/parent/teacher/admin).
current_user = get_current_user

# Базовый dependency-factory: пропустить только указанные роли.
# Возвращает 403 при несовпадении.
require_roles = require_role


# === Готовые shortcuts для частых случаев ===

def require_admin():
    """Только admin. Endpoint /admin/*."""
    return require_role(Role.ADMIN)


def require_teacher_or_admin():
    """Teacher или admin. Endpoint /materials/upload, /teacher/* (Sprint 1.2+)."""
    return require_role(Role.TEACHER, Role.ADMIN)


def require_parent():
    """Только parent. Endpoint /parents/* (кроме link-parent, там нужен student)."""
    return require_role(Role.PARENT)


def require_student():
    """Только student. Endpoint /students/link-parent и т.п."""
    return require_role(Role.STUDENT)


def require_teacher():
    """Только teacher (без admin — для будущих учительских эксклюзивных функций)."""
    return require_role(Role.TEACHER)


# === Type hints (не runtime-объекты) ===

# Импортируется как:
#   current: Annotated[User, Depends(require_teacher_or_admin())]
# или классически:
#   current: User = Depends(require_teacher_or_admin())

__all__ = [
    "Role",
    "User",
    "Session",
    "Depends",
    "get_db",
    "current_user",
    "require_roles",
    "require_admin",
    "require_teacher_or_admin",
    "require_teacher",
    "require_parent",
    "require_student",
]

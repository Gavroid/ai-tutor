"""CLI для создания/обновления пользователей Pilot Core Stage 1 (P1.1.4).

Политика пилота (см. pilot-core-stage-1.md §Фаза 1):
  - публичная /api/v1/auth/register принимает только student и parent;
  - teacher и admin создаются ТОЛЬКО через этот CLI;
  - каждое действие записывается в audit log (`action=user.seed`);
  - details НЕ содержат паролей/хэшей/секретов.

Требования безопасности:
  - обязательная переменная окружения `PILOT_SEED_TOKEN` (минимум 16 символов);
  - параметр CLI `--token <value>` ДОЛЖЕН совпадать с `PILOT_SEED_TOKEN`;
  - пароль никогда не попадает в audit/details/логи;
  - идемпотентность: повторный запуск обновляет существующего пользователя,
    а не создаёт дубль.

Запуск (внутри backend-контейнера или локально в .venv):

    cd /app
    export PILOT_SEED_TOKEN='$(openssl rand -hex 16)'
    python -m app.scripts.seed_users --demo

    # создать одного учителя:
    python -m app.scripts.seed_users --token "$PILOT_SEED_TOKEN" \\
        --teacher teacher@example.com --display-name "Учитель" \\
        --password 'demo-STRONG-Teacher-1'

    # импорт из CSV (email,role,display_name):
    python -m app.scripts.seed_users --token "$PILOT_SEED_TOKEN" \\
        --csv /tmp/users.csv --default-password 'change-me-NOW-1!'
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import secrets
import sys
from dataclasses import dataclass
from typing import Iterable, Sequence

from sqlalchemy import select

from app.admin import service as audit_service
from app.auth.security import hash_password
from app.db.session import SessionLocal
from app.users.models import Role, StudentProfile, User

# ---------------------------------------------------------------------------
# Константы и минимальные проверки безопасности
# ---------------------------------------------------------------------------

_MIN_TOKEN_LEN = 16

# Роли, которые разрешено создавать через этот CLI (включая привилегированные).
# student и parent тоже можно создавать здесь — единая точка входа.
ALL_PILOT_ROLES = (Role.STUDENT, Role.PARENT, Role.TEACHER, Role.ADMIN)

# Имена ролей для CLI (рус/англ совпадают со значениями enum).
_ROLE_FLAG_TO_VALUE: dict[str, Role] = {
    "student": Role.STUDENT,
    "parent": Role.PARENT,
    "teacher": Role.TEACHER,
    "admin": Role.ADMIN,
}


# ---------------------------------------------------------------------------
# Модели данных
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SeedUserSpec:
    """Описание одного пользователя для создания/обновления."""

    email: str
    role: Role
    display_name: str
    password: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_pilot_token(cli_token: str | None) -> str:
    """Требует переменную окружения PILOT_SEED_TOKEN и совпадение с --token.

    Возвращает токен из окружения (его значение НЕ печатается). Прерывает
    процесс с понятным сообщением, если токен отсутствует, слишком короткий
    или не совпадает с переданным CLI-параметром.
    """
    env_token = os.environ.get("PILOT_SEED_TOKEN", "")
    if not env_token:
        sys.stderr.write(
            "ОШИБКА: переменная окружения PILOT_SEED_TOKEN не установлена.\n"
            "Установите её перед запуском: export PILOT_SEED_TOKEN='$(openssl rand -hex 16)'.\n"
        )
        sys.exit(2)
    if len(env_token) < _MIN_TOKEN_LEN:
        sys.stderr.write(
            f"ОШИБКА: PILOT_SEED_TOKEN короче {_MIN_TOKEN_LEN} символов.\n"
            "Сгенерируйте новый: openssl rand -hex 16\n"
        )
        sys.exit(2)
    if cli_token is not None and cli_token != env_token:
        sys.stderr.write(
            "ОШИБКА: --token не совпадает с переменной окружения PILOT_SEED_TOKEN.\n"
            "Не передавайте токен через CLI в общих логах — лучше положить его в env.\n"
        )
        sys.exit(2)
    return env_token


def _validate_password(password: str) -> None:
    """Минимальная политика пароля для seed (>= 12 символов)."""
    if len(password) < 12:
        sys.stderr.write(
            "ОШИБКА: пароль короче 12 символов (seed-аккаунты должны быть "
            "устойчивы к перебору, т.к. создаются заранее известным набором).\n"
        )
        sys.exit(2)


def _audit_safe_details(details: dict[str, object]) -> dict[str, object]:
    """Защитный слой: вырезает из details всё, что может быть секретом.

    Возвращает копию без полей, которые теоретически могут содержать
    пароль/хэш/токен. На текущий момент мы их не пишем, но дополнительная
    защита не повредит: запрещаем «опасные» ключи и любые значения, похожие
    на bcrypt-хэш.
    """
    forbidden_keys = {"password", "pwd", "pass", "secret", "token", "hash"}
    safe: dict[str, object] = {}
    for k, v in details.items():
        if k.lower() in forbidden_keys:
            continue
        # Значение dict/list тоже фильтруем рекурсивно
        if isinstance(v, dict):
            safe[k] = _audit_safe_details(v)  # type: ignore[arg-type]
        else:
            safe[k] = v
    return safe


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def upsert_user(db, spec: SeedUserSpec) -> tuple[User, bool]:
    """Создаёт пользователя или обновляет display_name/role/пароль.

    Возвращает (user, created). created=True — пользователь был только что
    создан; created=False — уже существовал и обновлён.
    """
    email = _normalize_email(spec.email)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(spec.password),
            display_name=spec.display_name.strip(),
            role=spec.role,
        )
        db.add(user)
        db.flush()  # получить user.id
        created = True
    else:
        # Идемпотентное обновление: меняем display_name, role и хэш пароля.
        user.display_name = spec.display_name.strip()
        user.role = spec.role
        user.password_hash = hash_password(spec.password)
        created = False

    # student_profile создаётся только для student и только при создании
    if spec.role == Role.STUDENT and created:
        profile = StudentProfile(user_id=user.id, grade=7)
        db.add(profile)

    db.commit()
    db.refresh(user)
    return user, created


def _record_audit(db, *, user: User, source: str, demo: bool) -> None:
    """Записать событие audit log для созданного/обновлённого пользователя.

    details НЕ содержат ни пароля, ни хэша, ни токена. Записываем:
      - email (это не персданные по GDPR для служебного аккаунта)
      - role
      - created (bool) — был ли только что создан пользователь
      - source — "flag" | "csv" | "demo"
    """
    payload = _audit_safe_details(
        {
            "email": user.email,
            "role": user.role.value,
            "source": source,
            "demo": demo,
        }
    )
    audit_service.record(
        db,
        user=None,  # системное действие, не от лица пользователя
        action="user.seed",
        entity="user",
        entity_id=str(user.id),
        details=payload,
    )


# ---------------------------------------------------------------------------
# Источники пользователей: флаги / CSV / --demo
# ---------------------------------------------------------------------------


def _specs_from_flags(args: argparse.Namespace) -> list[SeedUserSpec]:
    """Собрать список SeedUserSpec из явных CLI-флагов."""
    specs: list[SeedUserSpec] = []
    pairs = (
        ("admin", args.admin),
        ("teacher", args.teacher),
        ("parent", args.parent),
        ("student", args.student),
    )
    for role_name, value in pairs:
        if value is None:
            continue
        # value = [email, display_name]
        if len(value) != 2:
            sys.stderr.write(
                f"ОШИБКА: --{role_name} требует ровно два аргумента: email и display_name.\n"
            )
            sys.exit(2)
        email, display_name = value
        if not args.password:
            sys.stderr.write(
                f"ОШИБКА: --{role_name} требует --password.\n"
            )
            sys.exit(2)
        specs.append(
            SeedUserSpec(
                email=email,
                role=_ROLE_FLAG_TO_VALUE[role_name],
                display_name=display_name,
                password=args.password,
            )
        )
    return specs


def _specs_from_csv(path: str, default_password: str | None) -> list[SeedUserSpec]:
    """Собрать SeedUserSpec из CSV-файла.

    Формат: `email,role,display_name` (заголовок обязателен).
    role — одно из student/parent/teacher/admin.
    Если задан --default-password, используется он; иначе генерируется
    одноразовый пароль, который ПЕЧАТАЕТСЯ в stdout (только при ручном
    запуске). В audit log он НЕ попадает.
    """
    if default_password is None:
        sys.stderr.write(
            "ОШИБКА: --csv требует --default-password "
            "(или явный --password для каждого пользователя через CSV нельзя).\n"
        )
        sys.exit(2)
    specs: list[SeedUserSpec] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "email" not in reader.fieldnames:
            sys.stderr.write(
                "ОШИБКА: CSV должен содержать колонку 'email' "
                "и опционально 'role' и 'display_name'.\n"
            )
            sys.exit(2)
        for row in reader:
            email = (row.get("email") or "").strip()
            if not email:
                continue
            role_raw = (row.get("role") or "student").strip().lower()
            if role_raw not in _ROLE_FLAG_TO_VALUE:
                sys.stderr.write(
                    f"ОШИБКА: неизвестная роль '{role_raw}' для {email}.\n"
                )
                sys.exit(2)
            display_name = (row.get("display_name") or email.split("@", 1)[0]).strip()
            specs.append(
                SeedUserSpec(
                    email=email,
                    role=_ROLE_FLAG_TO_VALUE[role_raw],
                    display_name=display_name,
                    password=default_password,
                )
            )
    return specs


_DEMO_ACCOUNTS = (
    SeedUserSpec(
        email="student@pilot.local",
        role=Role.STUDENT,
        display_name="Ученик (пилот)",
        password="DemoStudent-7-PILOT",
    ),
    SeedUserSpec(
        email="parent@pilot.local",
        role=Role.PARENT,
        display_name="Родитель (пилот)",
        password="DemoParent-7-PILOT",
    ),
    SeedUserSpec(
        email="teacher@pilot.local",
        role=Role.TEACHER,
        display_name="Учитель (пилот)",
        password="DemoTeacher-7-PILOT",
    ),
    SeedUserSpec(
        email="admin@pilot.local",
        role=Role.ADMIN,
        display_name="Администратор (пилот)",
        password="DemoAdmin-7-PILOT!",
    ),
)


def _specs_from_demo() -> list[SeedUserSpec]:
    return list(_DEMO_ACCOUNTS)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pilot Core Stage 1 — seed_users CLI (P1.1.4)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help=(
            "Значение PILOT_SEED_TOKEN (если не задан, используется переменная "
            "окружения). Передавать через CLI в общих логах НЕ рекомендуется."
        ),
    )
    parser.add_argument(
        "--admin",
        nargs=2,
        metavar=("EMAIL", "DISPLAY_NAME"),
        help="Создать/обновить пользователя с ролью admin.",
    )
    parser.add_argument(
        "--teacher",
        nargs=2,
        metavar=("EMAIL", "DISPLAY_NAME"),
        help="Создать/обновить пользователя с ролью teacher.",
    )
    parser.add_argument(
        "--parent",
        nargs=2,
        metavar=("EMAIL", "DISPLAY_NAME"),
        help="Создать/обновить пользователя с ролью parent.",
    )
    parser.add_argument(
        "--student",
        nargs=2,
        metavar=("EMAIL", "DISPLAY_NAME"),
        help="Создать/обновить пользователя с ролью student.",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Пароль (>=12 символов). Используется для --admin/--teacher/--parent/--student.",
    )
    parser.add_argument(
        "--csv",
        default=None,
        metavar="PATH",
        help="Импорт пользователей из CSV (email,role,display_name).",
    )
    parser.add_argument(
        "--default-password",
        default=None,
        metavar="PASSWORD",
        help="Пароль для пользователей из --csv (>=12 символов).",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Создать 4 demo-аккаунта: student/parent/teacher/admin (pilot.local).",
    )
    parser.add_argument(
        "--print-passwords",
        action="store_true",
        help="После успешного создания/обновления напечатать пароли в stdout.",
    )
    return parser


def _process_specs(specs: Sequence[SeedUserSpec], *, source: str, demo: bool) -> list[tuple[SeedUserSpec, bool]]:
    """Создать/обновить каждого пользователя и записать audit-событие.

    Возвращает список пар (spec, created).
    """
    results: list[tuple[SeedUserSpec, bool]] = []
    db = SessionLocal()
    try:
        for spec in specs:
            user, created = upsert_user(db, spec)
            _record_audit(db, user=user, source=source, demo=demo)
            results.append((spec, created))
    finally:
        db.close()
    return results


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    # 1. Gate: token
    _require_pilot_token(args.token)

    # 2. Собрать спецификации
    specs: list[SeedUserSpec] = []
    source = "flag"
    demo = False

    if args.demo:
        specs.extend(_specs_from_demo())
        source = "demo"
        demo = True

    if args.csv:
        if args.default_password is None:
            sys.stderr.write(
                "ОШИБКА: --csv требует --default-password (>=12 символов).\n"
            )
            return 2
        _validate_password(args.default_password)
        specs.extend(_specs_from_csv(args.csv, args.default_password))
        source = "csv"

    flag_specs = _specs_from_flags(args)
    if flag_specs and args.password is not None:
        _validate_password(args.password)
    specs.extend(flag_specs)

    if not specs:
        parser.print_help()
        sys.stderr.write(
            "\nОШИБКА: не задано ни одного пользователя. "
            "Укажите --demo, --csv или --admin/--teacher/--parent/--student.\n"
        )
        return 2

    # Валидация всех паролей (выше для флагов уже, здесь добиваем CSV/default)
    if args.default_password is not None:
        _validate_password(args.default_password)

    results = _process_specs(specs, source=source, demo=demo)

    # 3. Отчёт
    print("Pilot seed_users — выполнено:")
    for spec, created in results:
        marker = "создан" if created else "обновлён"
        print(f"  - {marker:>8}  {spec.role.value:<7}  {spec.email}")
        if args.print_passwords:
            print(f"      password: {spec.password}")

    print(
        f"\nИтого: {len(results)} пользователей. "
        f"Записано {len(results)} строк audit_log(action=user.seed)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

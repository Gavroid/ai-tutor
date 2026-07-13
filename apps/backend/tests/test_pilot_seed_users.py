"""Тесты Pilot Core Stage 1 — P1.1.4 (seed_users CLI).

Покрывают:
- аудит действие action=user.seed без секретов/паролей в details;
- обязательная переменная PILOT_SEED_TOKEN;
- явные флаги (--admin/--teacher/--parent/--student) и CSV (--csv);
- идемпотентность (повторный запуск обновляет, а не дублирует);
- --demo создаёт ровно 4 аккаунта в текущей настроенной БД;
- отсутствие паролей/хэшей в записях audit_log.

Запускаются в SQLite-in-memory, как и остальные backend тесты.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from app.db.session import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.users.models import User  # noqa: E402


PYTHON = sys.executable
BACKEND_DIR = Path(__file__).resolve().parent.parent
SEED_SCRIPT = BACKEND_DIR / "app" / "scripts" / "seed_users.py"


def _prepare_sqlite_db() -> str:
    """Drop/create all tables on the file-based SQLite DB used by the subprocess test.

    Using a file (vs `:memory:`) is required because each `subprocess.run`
    creates a fresh Python process, and SQLite in-memory databases are
    per-connection — the subprocess would not see the schema we just created.
    Returns the DB URL string so callers can pass it on.
    """
    import tempfile

    from app.db.session import engine as default_engine

    Base.metadata.drop_all(default_engine)
    default_engine.dispose()

    tmp = tempfile.NamedTemporaryFile(prefix="pilot_seed_", suffix=".sqlite", delete=False)
    tmp.close()
    db_path = tmp.name
    return f"sqlite+pysqlite:///{db_path}"


def _run_seed(env: dict[str, str], *args: str) -> subprocess.CompletedProcess:
    """Run the CLI script as a subprocess against the current SQLite test DB.

    Using a subprocess (rather than importing the module) proves the CLI works
    end-to-end and that PILOT_SEED_TOKEN is enforced at process level.
    """
    merged = os.environ.copy()
    merged.update(env)
    return subprocess.run(
        [PYTHON, "-m", "app.scripts.seed_users", *args],
        cwd=str(BACKEND_DIR),
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )


def _create_schema_in(db_url: str) -> None:
    """Create all tables in the given file-based SQLite DB.

    We re-import in a fresh engine so the subprocess's metadata reflects
    every model that Base.metadata knows about.
    """
    from sqlalchemy import create_engine as _create

    engine = _create(db_url)
    Base.metadata.create_all(engine)
    engine.dispose()


def test_seed_script_exists():
    """Pilot gate P1.1.4 requires apps/backend/app/scripts/seed_users.py."""
    assert SEED_SCRIPT.exists(), f"missing seed script at {SEED_SCRIPT}"


def test_seed_requires_pilot_seed_token():
    """Without PILOT_SEED_TOKEN the script must refuse to run."""
    db_url = _prepare_sqlite_db()
    _create_schema_in(db_url)
    env = {
        "APP_SECRET_KEY": "test-secret-key-for-pytest-only-1234567890",
        "DATABASE_URL": db_url,
        "PILOT_SEED_TOKEN": "",
    }
    proc = _run_seed(env, "--admin", "admin@example.com", "alice")
    assert proc.returncode != 0
    assert "PILOT_SEED_TOKEN" in (proc.stderr + proc.stdout)


def test_seed_rejects_wrong_pilot_seed_token():
    """If --token is supplied and doesn't match the env value, the CLI must refuse."""
    db_url = _prepare_sqlite_db()
    _create_schema_in(db_url)
    # Env token is "long-enough-12345678901234" (28 chars, >=16).
    # CLI token is a clearly mismatching value.
    env = {
        "APP_SECRET_KEY": "test-secret-key-for-pytest-only-1234567890",
        "DATABASE_URL": db_url,
        "PILOT_SEED_TOKEN": "env-token-correct-one-1234567890",
    }
    proc = _run_seed(
        env,
        "--token",
        "totally-different-bad-token-abcdef",
        "--admin",
        "admin@example.com",
        "Админ",
        "--password",
        "demoPass-Admin-1",
    )
    assert proc.returncode != 0
    assert "PILOT_SEED_TOKEN" in (proc.stderr + proc.stdout)


def test_seed_admin_via_flag_creates_user_and_audit():
    """--admin sets the admin role for the user and writes user.seed to audit log."""
    db_url = _prepare_sqlite_db()
    _create_schema_in(db_url)
    from sqlalchemy import create_engine, select

    from app.admin.models import AuditLog

    env = {
        "APP_SECRET_KEY": "test-secret-key-for-pytest-only-1234567890",
        "DATABASE_URL": db_url,
        "PILOT_SEED_TOKEN": "pilot-test-token-1234",
    }
    proc = _run_seed(
        env,
        "--admin",
        "admin@example.com",
        "Админ",
        "--password",
        "demoPass-Admin-1",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    # User row exists with role=admin
    eng = create_engine(db_url)
    with eng.connect() as conn:
        rows = list(conn.execute(select(User).where(User.email == "admin@example.com")))
    assert len(rows) == 1
    assert rows[0].role.value == "admin"

    # AuditLog row with action=user.seed exists
    eng = create_engine(db_url)
    with eng.connect() as conn:
        logs = list(conn.execute(select(AuditLog).where(AuditLog.action == "user.seed")))
    assert len(logs) >= 1

    # And critically — no password or hash leaked into details JSON.
    for log_row in logs:
        details = log_row.details
        if isinstance(details, str):
            details = json.loads(details)
        assert isinstance(details, dict), details
        flat = json.dumps(details, ensure_ascii=False).lower()
        assert "password" not in flat, f"password must not appear in audit details: {details}"
        assert "hash" not in flat, f"hash must not appear in audit details: {details}"
        assert "pass" not in flat or "compass" in flat or "bypass" in flat, (
            f"pass-like substring in details: {details}"
        )


def test_seed_is_idempotent_on_repeat():
    """Running the same flag twice must UPDATE the existing user, not create a duplicate."""
    db_url = _prepare_sqlite_db()
    _create_schema_in(db_url)
    env = {
        "APP_SECRET_KEY": "test-secret-key-for-pytest-only-1234567890",
        "DATABASE_URL": db_url,
        "PILOT_SEED_TOKEN": "pilot-test-token-1234",
    }
    proc1 = _run_seed(
        env,
        "--teacher",
        "teacher@example.com",
        "Учитель",
        "--password",
        "demoPass-Teach-1",
    )
    assert proc1.returncode == 0, proc1.stdout + proc1.stderr

    proc2 = _run_seed(
        env,
        "--teacher",
        "teacher@example.com",
        "Учитель",
        "--password",
        "demoPass-Teach-2-Rotated",
    )
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr

    # Exactly one user with that email
    from sqlalchemy import create_engine, select

    eng = create_engine(db_url)
    with eng.connect() as conn:
        rows = list(conn.execute(select(User).where(User.email == "teacher@example.com")))
    assert len(rows) == 1, f"seed should be idempotent, got {len(rows)} rows"


def test_seed_demo_creates_four_accounts():
    """--demo must create exactly the four roles in the configured DB."""
    db_url = _prepare_sqlite_db()
    _create_schema_in(db_url)
    env = {
        "APP_SECRET_KEY": "test-secret-key-for-pytest-only-1234567890",
        "DATABASE_URL": db_url,
        "PILOT_SEED_TOKEN": "pilot-test-token-1234",
    }
    proc = _run_seed(env, "--demo")
    assert proc.returncode == 0, proc.stdout + proc.stderr

    from sqlalchemy import create_engine, select

    eng = create_engine(db_url)
    with eng.connect() as conn:
        all_users = list(conn.execute(select(User)))
    roles = sorted({u.role.value for u in all_users})
    # Exactly the four pilot roles
    assert roles == ["admin", "parent", "student", "teacher"], roles
    assert len(all_users) == 4, f"expected 4 demo users, got {len(all_users)}"


def test_seed_csv_imports_multiple_users():
    """--csv accepts lines email,role,display_name and creates each user."""
    db_url = _prepare_sqlite_db()
    _create_schema_in(db_url)
    csv_path = Path("/tmp/pilot_seed_users.csv")
    csv_path.write_text(
        "email,role,display_name\n"
        "csv-a@example.com,student,A\n"
        "csv-b@example.com,parent,B\n",
        encoding="utf-8",
    )
    env = {
        "APP_SECRET_KEY": "test-secret-key-for-pytest-only-1234567890",
        "DATABASE_URL": db_url,
        "PILOT_SEED_TOKEN": "pilot-test-token-1234",
    }
    proc = _run_seed(
        env,
        "--csv",
        str(csv_path),
        "--default-password",
        "csv-Default-1-DEMO",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    from sqlalchemy import create_engine, select

    eng = create_engine(db_url)
    with eng.connect() as conn:
        rows = list(conn.execute(select(User)))
    emails = sorted(u.email for u in rows)
    assert "csv-a@example.com" in emails
    assert "csv-b@example.com" in emails


def test_seed_audit_details_must_not_contain_secret_or_password():
    """Final audit-friendly check: walk every user.seed row and verify no secret leak."""
    db_url = _prepare_sqlite_db()
    _create_schema_in(db_url)
    env = {
        "APP_SECRET_KEY": "test-secret-key-for-pytest-only-1234567890",
        "DATABASE_URL": db_url,
        "PILOT_SEED_TOKEN": "pilot-test-token-1234",
    }
    proc = _run_seed(env, "--demo")
    assert proc.returncode == 0, proc.stdout + proc.stderr

    from sqlalchemy import create_engine, select

    from app.admin.models import AuditLog

    eng = create_engine(db_url)
    with eng.connect() as conn:
        logs = list(conn.execute(select(AuditLog).where(AuditLog.action == "user.seed")))

    assert len(logs) >= 4, "expected at least one audit row per created demo user"
    for log_row in logs:
        details = log_row.details
        if isinstance(details, str):
            details = json.loads(details)
        assert isinstance(details, dict)
        flat = json.dumps(details, ensure_ascii=False).lower()
        assert "password" not in flat
        assert "hash" not in flat
        assert "secret" not in flat

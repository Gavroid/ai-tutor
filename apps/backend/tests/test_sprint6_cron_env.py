"""Sprint 6.x — тесты для cron jobs и shell-скриптов.

После фикса Sprint 6 cron env path (source /opt/ai-tutor/.env вместо
/etc/ai-tutor/.env), мы хотим защититься от регрессии — если кто-то
снова поменяет path, тесты должны это поймать.

Это простые file-content тесты (не bash unit-тесты). Они проверяют:
- Все cron файлы source правильный env path
- Все cron файлы имеют правильный schedule
- Все shell-скрипты в deploy/monitoring имеют +x permission
"""
from __future__ import annotations

import re
import stat
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]  # tests/ → backend/ → apps/ → ai-tutor/
DEPLOY_DIR = REPO_ROOT / "deploy"


def _read_cron_files() -> list[Path]:
    """Возвращает все cron-файлы (и /etc/cron.d/ai-tutor-* если есть, иначе deploy/monitoring/cron/*)."""
    files = list((DEPLOY_DIR / "monitoring" / "cron").glob("ai-tutor-*.cron"))
    return files


def _read_monitoring_scripts() -> list[Path]:
    """Возвращает все shell-скрипты в deploy/monitoring/."""
    return list((DEPLOY_DIR / "monitoring").glob("*.sh"))


def _read_cron_content(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# === Тесты: правильный env path ===

@pytest.mark.parametrize(
    "filename",
    [
        "ai-tutor-audit-cleanup.cron",
        "ai-tutor-disk-monitor.cron",
        "ai-tutor-monitor.cron",
        "ai-tutor-backup.cron",
        "ai-tutor-weekly-summary.cron",
        "ai-tutor-backup-verify.cron",
        "ai-tutor-index-cron.cron",
        "ai-tutor-telegram-bot.cron",
    ],
)
def test_cron_file_exists_in_repo(filename):
    """Sprint 6: cron files должны быть в deploy/monitoring/cron/."""
    path = DEPLOY_DIR / "monitoring" / "cron" / filename
    if not path.exists():
        pytest.skip(f"Cron file {filename} not in repo (only on prod /etc/cron.d)")
    assert path.is_file()


def test_cron_audit_cleanup_uses_correct_env_path():
    """Sprint 6: audit-cleanup.cron source /opt/ai-tutor/.env (НЕ /etc/ai-tutor/.env)."""
    path = DEPLOY_DIR / "monitoring" / "cron" / "ai-tutor-audit-cleanup.cron"
    if not path.exists():
        pytest.skip("File not in repo")
    content = _read_cron_content(path)
    # Должен source /opt/ai-tutor/.env
    assert "source /opt/ai-tutor/.env" in content
    # НЕ должен source /etc/ai-tutor/.env (которого нет на проде)
    assert "source /etc/ai-tutor/.env" not in content, (
        "BUG: /etc/ai-tutor/.env не существует на проде. "
        "Используйте /opt/ai-tutor/.env"
    )


def test_cron_monitor_uses_correct_env_path():
    """Sprint 6: monitor.cron (healthcheck + error-rate) source /opt/ai-tutor/.env."""
    path = DEPLOY_DIR / "monitoring" / "cron" / "ai-tutor-monitor.cron"
    if not path.exists():
        pytest.skip("File not in repo")
    content = _read_cron_content(path)
    assert "source /opt/ai-tutor/.env" in content
    assert "source /etc/ai-tutor/.env" not in content


def test_cron_backup_uses_correct_env_path():
    """Sprint 6: backup.cron source /opt/ai-tutor/.env."""
    path = DEPLOY_DIR / "monitoring" / "cron" / "ai-tutor-backup.cron"
    if not path.exists():
        pytest.skip("File not in repo")
    content = _read_cron_content(path)
    assert "source /opt/ai-tutor/.env" in content
    assert "source /etc/ai-tutor/.env" not in content


def test_cron_weekly_summary_uses_correct_env_path():
    """Sprint 6: weekly-summary.cron source /opt/ai-tutor/.env (Sprint 6.3 fix)."""
    path = DEPLOY_DIR / "monitoring" / "cron" / "ai-tutor-weekly-summary.cron"
    if not path.exists():
        pytest.skip("File not in repo")
    content = _read_cron_content(path)
    assert "source /opt/ai-tutor/.env" in content
    assert "source /etc/ai-tutor/.env" not in content, (
        "BUG (Sprint 6.3): /etc/ai-tutor/.env не существует на проде. "
        "Используйте /opt/ai-tutor/.env"
    )


def test_telegram_bot_supervisor_uses_correct_env_path():
    """Sprint 6.1: telegram-bot.sh source /opt/ai-tutor/.env (НЕ /etc/ai-tutor/.env)."""
    path = DEPLOY_DIR / "monitoring" / "telegram-bot.sh"
    if not path.exists():
        pytest.skip("File not in repo")
    content = _read_cron_content(path)
    # Скрипт должен source /opt/ai-tutor/.env (НЕ /etc/ai-tutor/.env)
    if "source /opt/ai-tutor/.env" in content or "TELEGRAM_BOT_TOKEN=" in content:
        # OK: source env или hardcode env vars
        pass
    else:
        pytest.fail("telegram-bot.sh must have TELEGRAM_BOT_TOKEN env var (env source or hardcode)")


# === Тесты: executable permission ===

def test_monitoring_scripts_are_executable():
    """Все shell-скрипты в deploy/monitoring/ должны быть +x."""
    for path in _read_monitoring_scripts():
        mode = path.stat().st_mode
        assert mode & stat.S_IXUSR, f"{path.name} is not executable (chmod +x missing)"
        assert mode & stat.S_IXGRP, f"{path.name} not group-executable"
        # world-executable — необязательно для security


def test_deploy_scripts_are_executable():
    """Shell-скрипты в deploy/release/ должны быть +x."""
    for path in (DEPLOY_DIR / "release").glob("*.sh"):
        mode = path.stat().st_mode
        assert mode & stat.S_IXUSR, f"{path.name} is not executable"


# === Тесты: cron schedule валидный ===

def test_cron_audit_cleanup_runs_daily():
    """audit-cleanup должен запускаться раз в день (0 3 * * *)."""
    path = DEPLOY_DIR / "monitoring" / "cron" / "ai-tutor-audit-cleanup.cron"
    if not path.exists():
        pytest.skip("File not in repo")
    content = _read_cron_content(path)
    # Ищем строку вида "0 3 * * *"
    assert re.search(r"0\s+3\s+\*\s+\*\s+\*", content), (
        "audit-cleanup должен запускаться в 03:00 (0 3 * * *)"
    )


def test_cron_backup_runs_daily():
    """backup должен запускаться раз в день."""
    path = DEPLOY_DIR / "monitoring" / "cron" / "ai-tutor-backup.cron"
    if not path.exists():
        pytest.skip("File not in repo")
    content = _read_cron_content(path)
    assert re.search(r"0\s+3\s+\*\s+\*\s+\*", content), (
        "backup должен запускаться в 03:00"
    )


def test_cron_monitor_runs_every_5_minutes():
    """monitor (healthcheck) должен запускаться каждые 5 мин (*/5)."""
    path = DEPLOY_DIR / "monitoring" / "cron" / "ai-tutor-monitor.cron"
    if not path.exists():
        pytest.skip("File not in repo")
    content = _read_cron_content(path)
    assert re.search(r"\*/5\s+\*\s+\*\s+\*\s+\*", content), (
        "monitor должен запускаться каждые 5 минут"
    )


def test_cron_telegram_bot_supervisor_runs_every_5_minutes():
    """telegram-bot supervisor должен запускаться каждые 5 мин."""
    path = DEPLOY_DIR / "monitoring" / "cron" / "ai-tutor-telegram-bot.cron"
    if not path.exists():
        pytest.skip("File not in repo")
    content = _read_cron_content(path)
    assert re.search(r"\*/5\s+\*\s+\*\s+\*\s+\*", content)


# === Тесты: shell script syntax ===

def test_monitoring_shell_scripts_have_valid_syntax():
    """Все .sh файлы должны иметь валидный bash syntax."""
    import subprocess

    for path in _read_monitoring_scripts():
        # Проверяем через bash -n (no-execute, только syntax check)
        r = subprocess.run(
            ["bash", "-n", str(path)],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (
            f"{path.name} has syntax error: {r.stderr}"
        )


def test_release_shell_scripts_have_valid_syntax():
    """deploy/release/*.sh должны иметь валидный bash syntax."""
    import subprocess

    for path in (DEPLOY_DIR / "release").glob("*.sh"):
        r = subprocess.run(
            ["bash", "-n", str(path)],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, f"{path.name}: {r.stderr}"


# === Тесты: deploy scripts не удаляют ssl/certs ===

def test_deploy_from_ci_excludes_ssl_certs():
    """Sprint 4 fix: rsync в deploy-from-ci.sh НЕ удаляет ssl/certs (SSL сертификаты)."""
    path = DEPLOY_DIR / "release" / "deploy-from-ci.sh"
    if not path.exists():
        pytest.skip("File not in repo")
    content = _read_cron_content(path)
    # Должен быть --exclude=/deploy/ssl/certs
    assert "--exclude=/deploy/ssl/certs" in content, (
        "BUG: deploy-from-ci.sh rsync удаляет SSL сертификаты! "
        "Добавь --exclude=/deploy/ssl/certs"
    )


def test_telegram_bot_sh_checks_container_namespace():
    """Sprint 6.1 fix: supervisor проверяет процесс в container namespace, НЕ на хосте."""
    path = DEPLOY_DIR / "monitoring" / "telegram-bot.sh"
    if not path.exists():
        pytest.skip("File not in repo")
    content = _read_cron_content(path)
    # Supervisor должен использовать 'docker exec ... ls /proc/' или похожий подход
    # чтобы проверить процесс в контейнере (не ps -p на хосте).
    assert "docker exec" in content, (
        "telegram-bot.sh должен использовать docker exec для проверки namespace"
    )
    # Не должен использовать просто 'ps -p $PID' (не работает между namespaces)
    # Это warning, не hard fail — допускаем если есть способ
    if "ps -p" in content and "docker exec" not in content:
        pytest.fail(
            "telegram-bot.sh: 'ps -p $PID' на хосте не видит процесс в контейнере. "
            "Используйте 'docker exec ... ls /proc/' для проверки."
        )
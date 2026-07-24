"""Sprint 32 P3 — TOTP 2FA service для parent.

Использует pyotp для генерации/проверки TOTP-кодов.
Secret шифруется через Fernet (settings.encryption_key).
Backup codes хэшируются bcrypt (cost=12).
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pyotp
from cryptography.fernet import Fernet

from app.auth.security import hash_password, verify_password
from app.config import get_settings
from app.db.session import engine as _engine
from sqlalchemy import select, text

if TYPE_CHECKING:
    from app.users.models import Parent2FA


_BACKUP_CODE_COUNT = 8
_BACKUP_CODE_LENGTH = 12  # 12 hex chars = 48 bits entropy


def _get_fernet() -> Fernet:
    """Получает Fernet cipher из settings.

    encryption_key берётся из APP_SECRET_KEY-derived key.
    Sprint 32 NOTE: используем SHA256 hash как Fernet key (32 bytes, base64).
    """
    import base64
    import hashlib

    settings = get_settings()
    # Derive 32-byte key из APP_SECRET_KEY через SHA256
    key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.app_secret_key.encode()).digest()
    )
    return Fernet(key)


def encrypt_secret(secret: str) -> str:
    """Шифрует TOTP secret через Fernet."""
    return _get_fernet().encrypt(secret.encode()).decode()


def decrypt_secret(encrypted: str) -> str:
    """Расшифровывает TOTP secret через Fernet."""
    return _get_fernet().decrypt(encrypted.encode()).decode()


def generate_secret() -> str:
    """Генерирует новый TOTP secret (base32)."""
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str) -> str:
    """Генерирует provisioning URI для QR-кода.

    Формат: otpauth://totp/AI-Tutor:email?secret=...&issuer=AI-Tutor
    """
    return pyotp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name="AI-Tutor",
    )


def verify_totp(secret: str, code: str) -> bool:
    """Проверяет TOTP код с допустимым окном ±1 (30 сек).

    Возвращает True если код верный.
    """
    if not code or len(code) != 6 or not code.isdigit():
        return False
    totp = pyotp.TOTP(secret)
    # valid_window=1 допускает ±1 шаг (30 сек до и после).
    return totp.verify(code, valid_window=1)


def generate_backup_codes() -> list[str]:
    """Генерирует 8 одноразовых backup codes.

    Каждый код: 12 hex chars (48 bits entropy).
    Sprint 32 NOTE: хэшируются bcrypt перед сохранением.
    """
    return [
        secrets.token_hex(_BACKUP_CODE_LENGTH // 2).upper()
        for _ in range(_BACKUP_CODE_COUNT)
    ]


def hash_backup_codes(codes: list[str]) -> str:
    """Хэширует backup codes через bcrypt и сохраняет как JSON list."""
    return json.dumps([hash_password(c) for c in codes])


def verify_backup_code(parent_id: int, code: str) -> bool:
    """Проверяет backup code. Удаляет использованный.

    Возвращает True если code валидный и не использован ранее.
    """
    engine = _engine
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT backup_codes_json FROM parent_2fa WHERE parent_id = :pid"),
            {"pid": parent_id},
        ).fetchone()
        if row is None:
            return False
        hashed = json.loads(row[0])
        # Проверяем каждый хэш
        for i, h in enumerate(hashed):
            if verify_password(code, h):
                # Удаляем использованный
                new_hashed = hashed[:i] + hashed[i + 1 :]
                conn.execute(
                    text(
                        "UPDATE parent_2fa SET backup_codes_json = :h, "
                        "last_used_at = :ts WHERE parent_id = :pid"
                    ),
                    {
                        "h": json.dumps(new_hashed),
                        "ts": datetime.now(timezone.utc),
                        "pid": parent_id,
                    },
                )
                return True
    return False


def has_2fa_enabled(parent_id: int) -> bool:
    """Проверяет есть ли у parent 2FA enabled."""
    engine = _engine
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM parent_2fa WHERE parent_id = :pid"),
            {"pid": parent_id},
        ).fetchone()
    return result is not None


def enable_2fa(parent_id: int, email: str) -> dict:
    """Включает 2FA для parent.

    Возвращает dict с secret (только для QR-code) и backup_codes.
    Sprint 32 NOTE: secret и codes возвращаются ТОЛЬКО при enable.
    Пере-enable требует disable сначала.
    """
    if has_2fa_enabled(parent_id):
        raise ValueError(f"2FA already enabled for parent_id={parent_id}")

    secret = generate_secret()
    codes = generate_backup_codes()

    engine = _engine
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO parent_2fa "
                "(parent_id, secret_encrypted, backup_codes_json, enabled_at) "
                "VALUES (:pid, :sec, :codes, :ts)"
            ),
            {
                "pid": parent_id,
                "sec": encrypt_secret(secret),
                "codes": hash_backup_codes(codes),
                "ts": datetime.now(timezone.utc),
            },
        )

    return {
        "secret": secret,  # base32 (для QR-code provisioning)
        "provisioning_uri": provisioning_uri(secret, email),
        "backup_codes": codes,  # plaintext (один раз!)
    }


def disable_2fa(parent_id: int) -> None:
    """Отключает 2FA для parent."""
    engine = _engine
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM parent_2fa WHERE parent_id = :pid"),
            {"pid": parent_id},
        )


def authenticate_2fa(parent_id: int, code_or_backup: str) -> bool:
    """Проверяет TOTP code ИЛИ backup code.

    Возвращает True если parent прошёл 2FA.
    Сначала пробует TOTP (6 digits), потом backup (12 hex).
    """
    if not has_2fa_enabled(parent_id):
        # Если 2FA не включена, родитель уже аутентифицирован.
        return True

    engine = _engine
    with engine.connect() as conn:
        encrypted = conn.execute(
            text("SELECT secret_encrypted FROM parent_2fa WHERE parent_id = :pid"),
            {"pid": parent_id},
        ).scalar()

    if encrypted is None:
        return False

    secret = decrypt_secret(encrypted)

    # TOTP code (6 digits)?
    if len(code_or_backup) == 6 and code_or_backup.isdigit():
        if verify_totp(secret, code_or_backup):
            _update_last_used(parent_id)
            return True
        return False

    # Backup code (12 hex chars)?
    return verify_backup_code(parent_id, code_or_backup)


def _update_last_used(parent_id: int) -> None:
    """Обновляет last_used_at для аудита."""
    engine = _engine
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE parent_2fa SET last_used_at = :ts WHERE parent_id = :pid"),
            {"ts": datetime.now(timezone.utc), "pid": parent_id},
        )
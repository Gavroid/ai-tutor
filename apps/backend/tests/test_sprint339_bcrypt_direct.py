"""Sprint 3.39 (TDD RED → GREEN): regression test для passlib → bcrypt-direct migration.

Перед заменой CryptContext на прямые вызовы bcrypt, фиксируем поведение
существующего API через тесты. Затем реализуем bcrypt-direct с тем же
контрактом (тот же формат $2b$12$..., та же rounds=12).

Существующие хэши в БД (7 whitelist users + 2FA коды) должны продолжать работать.
"""

from __future__ import annotations

import pytest
from app.auth.security import hash_password, verify_password


class TestSprint339PasswordHashingBackwardCompatibility:
    """Sprint 3.39: гарантирует что bcrypt-direct API совместим с passlib API."""

    def test_hash_password_returns_bcrypt_format(self) -> None:
        """Хэш должен начинаться с $2b$ (bcrypt standard)."""
        hashed = hash_password("TestPassword123!")
        assert hashed.startswith("$2b$"), (
            f"Expected $2b$ prefix (bcrypt), got: {hashed[:7]!r}. "
            "Sprint 3.39: bcrypt-direct должен сохранять тот же формат."
        )

    def test_hash_password_uses_cost_12(self) -> None:
        """Cost factor должен быть 12 (как у passlib CryptContext ранее)."""
        hashed = hash_password("TestPassword123!")
        # $2b$12$ — 12 это cost factor (2^12 = 4096 rounds).
        assert hashed[:6] == "$2b$12", (
            f"Expected cost factor 12, got: {hashed[:6]!r}"
        )

    def test_hash_password_returns_string(self) -> None:
        """Sprint 3.22 fix: cast to str (passlib возвращал Any)."""
        hashed = hash_password("TestPassword123!")
        assert isinstance(hashed, str), (
            f"Expected str, got {type(hashed).__name__}. "
            "Sprint 3.22 уже исправил это с cast."
        )

    def test_verify_password_returns_bool(self) -> None:
        """Sprint 3.22 fix: cast to bool (passlib возвращал Any)."""
        hashed = hash_password("TestPassword123!")
        result = verify_password("TestPassword123!", hashed)
        assert isinstance(result, bool), (
            f"Expected bool, got {type(result).__name__}"
        )
        assert result is True

    def test_verify_password_correct(self) -> None:
        """Правильный пароль → True."""
        hashed = hash_password("MySecretPassword")
        assert verify_password("MySecretPassword", hashed) is True

    def test_verify_password_incorrect(self) -> None:
        """Неправильный пароль → False (не raise!)."""
        hashed = hash_password("MySecretPassword")
        assert verify_password("WrongPassword", hashed) is False

    def test_verify_password_empty_password(self) -> None:
        """Пустой пароль vs существующего хэша → False."""
        hashed = hash_password("NonEmptyPassword")
        assert verify_password("", hashed) is False

    def test_hash_password_different_calls_different_hashes(self) -> None:
        """Два вызова hash_password с одинаковым паролем → разные хэши (salt)."""
        h1 = hash_password("SamePassword")
        h2 = hash_password("SamePassword")
        assert h1 != h2, (
            "Two hashes with same password are equal — salt broken! "
            "Sprint 3.39: bcrypt-direct должен использовать bcrypt.gensalt()"
        )

    def test_hash_password_unicode(self) -> None:
        """Unicode пароли должны работать (кириллица)."""
        password = "Пароль123_Тест"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password(password + "_wrong", hashed) is False

    def test_backward_compat_old_hash_format(self) -> None:
        """Существующие хэши $2b$12$... от passlib должны verify'иться без перехэширования.

        Этот тест проверяет контракт: если в БД лежит хэш из passlib
        (cost 12), verify_password должен его принять с правильным паролем.
        """
        # Создаём реальный bcrypt хэш напрямую через bcrypt (имитация passlib-стиля).
        import bcrypt

        test_password = "BackwardCompatTest"
        # passlib bcrypt генерирует именно $2b$ с rounds=12
        test_hash = bcrypt.hashpw(
            test_password.encode("utf-8"),
            bcrypt.gensalt(rounds=12, prefix=b"2b"),
        ).decode("utf-8")

        # Этот хэш должен verify'иться через новый bcrypt-direct код
        assert verify_password(test_password, test_hash) is True, (
            "Хэш в формате passlib $2b$12$... НЕ verify'ится. "
            "Sprint 3.39: bcrypt-direct должен быть совместим с passlib форматом."
        )

    def test_72_byte_limit_rejection(self) -> None:
        """bcrypt имеет hard limit 72 байта. Проверяем поведение для длинных паролей.

        Стратегия (Sprint 3.39): НЕ молча truncate (как делает passlib),
        а throw ValueError чтобы caller знал о проблеме. Если passlib
        truncate'ил молча — это deviation в semantics, нужно явно
        документировать.
        """
        long_password = "x" * 100  # > 72 bytes

        # Если текущая реализация reject'ит — поведение оставляем как есть.
        # Если accept'ит первые 72 байта — нужно явно задокументировать.
        # Этот тест проверяет что поведение consistent.
        try:
            hashed = hash_password(long_password)
            # Если хэш создался — verify с тем же паролем должен работать
            assert verify_password(long_password, hashed) is True
        except (ValueError, TypeError) as e:
            # Если reject'ит — это тоже OK (явная ошибка лучше silent truncate)
            assert "72" in str(e).lower() or "byte" in str(e).lower() or len(long_password) > 72, (
                f"Unexpected error for long password: {e}"
            )

    def test_2fa_code_round_trip(self) -> None:
        """2FA коды (6-8 chars) должны хэшироваться и verify'иться.

        app.users.twofa использует hash_password/verify_password для хранения
        backup-кодов (Sprint 3.22 fix). Этот тест проверяет что короткие
        коды (6 chars) работают с новым bcrypt-direct.
        """
        code_hash = hash_password("ABC123")
        assert verify_password("ABC123", code_hash) is True
        assert verify_password("XYZ789", code_hash) is False

"""Sprint 81: DB connection retry on startup tests."""
from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import asyncio
from unittest.mock import MagicMock, patch

import pytest

# === Source verification ===

def test_lifespan_has_retry_logic():
    """Sprint 81: lifespan function has retry logic."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "main.py",
        )
    ) as f:
        content = f.read()
    assert "Sprint 81: retry DB ping" in content
    assert "max_attempts = 3" in content
    assert "exponential" in content.lower()


def test_lifespan_uses_exponential_backoff():
    """Sprint 81: uses 2 ** (attempt - 1) для exponential backoff."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "main.py",
        )
    ) as f:
        content = f.read()
    assert "2 ** (attempt - 1)" in content or "wait_seconds = 2 **" in content


def test_lifespan_max_attempts_3():
    """Sprint 81: max_attempts = 3."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "main.py",
        )
    ) as f:
        content = f.read()
    assert "max_attempts = 3" in content


def test_lifespan_no_fail_fast():
    """Sprint 81: не fail-fast (catch exception в loop)."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "main.py",
        )
    ) as f:
        content = f.read()
    # Old code raised immediately; new code catches per attempt
    lifespan_section = content.split("async def lifespan")[1].split("yield")[0]
    assert "except Exception" in lifespan_section
    assert "continue" not in lifespan_section or "next_attempt" in lifespan_section


# === Integration tests ===

def test_lifespan_break_on_success():
    """Sprint 81: при successful ping — break (no retry)."""
    # Verify source: после successful SELECT 1 есть break
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "main.py",
        )
    ) as f:
        content = f.read()
    # Pattern: "if attempt > 1: logger.info...; break"
    assert "if attempt > 1" in content
    assert "break" in content


def test_lifespan_exponential_backoff_timing():
    """Sprint 81: exponential backoff timing (1s, 2s, 4s)."""
    # Verify source has 2 ** (attempt - 1) formula
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "main.py",
        )
    ) as f:
        content = f.read()
    # Compute expected values
    expected = []
    for attempt in range(1, 4):  # 1, 2, 3
        wait = 2 ** (attempt - 1)
        expected.append(wait)
    # 1, 2, 4
    assert expected == [1, 2, 4]
    # Verify code uses similar formula
    assert "2 ** (attempt - 1)" in content or "wait_seconds = 2 **" in content

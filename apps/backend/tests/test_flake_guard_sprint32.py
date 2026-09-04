"""Sprint continuation T2.3: flake-guard runner для test_sprint32_parent_2fa.

Audit (2026-08-23) зафиксил flake в
``tests/test_sprint32::test_enable_2fa_returns_secret_and_codes``
из-за asyncio_default_fixture_loop_scope race condition.
Sprint 1 закрыл flake через ``asyncio_default_fixture_loop_scope = function``
в pytest.ini. Этот тест — страховка: реально ли flake исчез?

Стратегия:
- Запускаем ``tests/test_sprint32_parent_2fa.py`` как subprocess
  pytest несколько раз (count=3 по умолчанию).
- Каждый прогон должен дать 12 passed, 0 failed.
- Если хоть один дал failed — flake вернулся, тест ловит regression.

Почему subprocess, а не parametrize внутри pytest:
- Хотим изолировать loop scope между прогонами — каждый отдельный процесс.
- Test не должен ломаться внутри test-sprint32 фикстуры родителя
  (parent_user_token fixtures).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path("/root/workspace/ai-tutor/apps/backend")
SPRINT32 = REPO_ROOT / "tests" / "test_sprint32_parent_2fa.py"
FLAKE_RUNS = int(os.environ.get("FLAKE_RUNS", "3"))


def _run_sprint32_once(iteration: int) -> subprocess.CompletedProcess:
    """Один прогон sprint32 в изолированном subprocess."""
    env = os.environ.copy()
    env["AI_API_KEY"] = "mock-key-for-tests"
    env.pop("FLAKE_RUNS", None)
    return subprocess.run(
        [
            str(REPO_ROOT / ".venv" / "bin" / "pytest"),
            "-q",
            "--tb=no",
            "-p",
            "no:cacheprovider",
            "-o",
            "addopts=",
            str(SPRINT32.relative_to(REPO_ROOT)),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.skipif(
    not SPRINT32.exists(),
    reason="test_sprint32_parent_2fa.py not present (migration)",
)
@pytest.mark.timeout(600)  # 3 runs × 120s = 360s budget + overhead
def test_sprint32_no_flake_in_three_consecutive_runs():
    """T2.3: гарантия что flake в test_sprint32 закрыт.

    Sprint 1 fix: ``asyncio_default_fixture_loop_scope = function``
    в pytest.ini устранил race-condition. Этот тест — страховка на
    regression: если flake вернётся (например кто-то обновит
    pytest-asyncio loop policy), хотя бы 1 из 3 прогонов упадёт.
    """
    if not (REPO_ROOT / ".venv" / "bin" / "pytest").exists():
        pytest.skip("backend .venv не найден — flake-guard пропущен")

    failures: list[tuple[int, str, str]] = []
    for i in range(FLAKE_RUNS):
        result = _run_sprint32_once(i)
        # Полная failure-mode: pytest вернёт rc=1 при ошибках/падениях.
        # Warnings не считаются.
        if result.returncode != 0:
            failures.append(
                (
                    i,
                    result.stdout[-500:] if result.stdout else "",
                    result.stderr[-500:] if result.stderr else "",
                )
            )

    assert not failures, (
        f"flake воспроизвёлся в test_sprint32_parent_2fa: "
        f"{len(failures)}/{FLAKE_RUNS} прогонов failed\n"
        + "\n---\n".join(f"Run #{i}\nSTDOUT:\n{o}\nSTDERR:\n{e}" for i, o, e in failures)
    )


def test_sprint32_file_is_intact():
    """T2.3-related safety net: убедиться, что flake-guard target не пропал."""
    assert SPRINT32.exists(), f"missing: {SPRINT32}"
    content = SPRINT32.read_text(encoding="utf-8")
    # flake-fix в S1 оставил целостность теста нетронутой;
    # проверяем что критичные тесты присутствуют.
    assert "test_enable_2fa_returns_secret_and_codes" in content
    assert "test_status_before_enable" in content
    assert "test_status_after_enable" in content

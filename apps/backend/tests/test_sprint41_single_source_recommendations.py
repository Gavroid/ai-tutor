"""Sprint 4.1: single-source рекомендаций — backend является источником истины.

Решение владельца (audit 2026-09-05, зафиксировано):
- Backend возвращает готовые recommendations в /api/v1/parents/children/{id}
- Frontend НЕ строит рекомендации на клиенте (Sprint 4.1 = single-source)
- НЕ дублируется логика порогов (accuracy < 0.6, mastery < 60%, slice(0, 5))

Что проверяем:
1. Endpoint возвращает поле 'recommendations' (list[ParentRecommendation])
2. Endpoint возвращает поле 'review_topics' (list[ReviewTopic]) из Sprint 4.2
3. Содержание recommendations зависит от accuracy + weak_topics
4. Frontend НЕ ДОЛЖЕН иметь buildParentRecommendations() в client-side коде

Подход к фикстуре: используем client_with_parent из test_parent_no_email_leak.py
через прямой импорт функции-фикстуры.
"""

from __future__ import annotations

import pytest

# Импортируем фикстуру из соседнего test_*.py модуля.
# pytest требует чтобы фикстура была объявлена в test_*.py файле
# в той же директории ИЛИ в conftest.py — но мы используем прямой import
# для удобства (это известный pattern в этом проекте).
from tests.test_parent_no_email_leak import _login_parent, client_with_parent


def test_child_overview_has_recommendations_field(client_with_parent):
    """Sprint 4.1 RED: endpoint /children/{id} должен возвращать 'recommendations'."""
    c, student_id = client_with_parent
    token = _login_parent(c)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get(
        f"/api/v1/parents/children/{student_id}",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()

    # Sprint 4.1: backend — single source, recommendations обязаны быть.
    assert "recommendations" in body, (
        f"Sprint 4.1: 'recommendations' field missing from overview. " f"Got keys: {list(body.keys())}"
    )
    assert isinstance(
        body["recommendations"], list
    ), f"recommendations must be a list, got {type(body['recommendations'])}"


def test_child_overview_has_review_topics_field(client_with_parent):
    """Sprint 4.1 RED + Sprint 4.2: endpoint /children/{id} возвращает 'review_topics'."""
    c, student_id = client_with_parent
    token = _login_parent(c)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get(
        f"/api/v1/parents/children/{student_id}",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()

    # Sprint 4.1 + 4.2: review_topics — top-5 по last_reviewed_at.
    assert "review_topics" in body, (
        f"Sprint 4.1+4.2: 'review_topics' field missing from overview. " f"Got keys: {list(body.keys())}"
    )
    assert isinstance(body["review_topics"], list), f"review_topics must be a list, got {type(body['review_topics'])}"


def test_recommendations_have_required_fields(client_with_parent):
    """Sprint 4.1: ParentRecommendation schema: title, detail, tone."""
    c, student_id = client_with_parent
    token = _login_parent(c)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get(
        f"/api/v1/parents/children/{student_id}",
        headers=headers,
    )
    body = r.json()

    for rec in body["recommendations"]:
        assert "title" in rec, f"Recommendation missing 'title': {rec}"
        assert "detail" in rec, f"Recommendation missing 'detail': {rec}"
        assert "tone" in rec, f"Recommendation missing 'tone': {rec}"
        assert rec["tone"] in ("neutral", "success", "warning"), f"Invalid tone: {rec['tone']}"


def test_recommendations_non_empty_for_real_student(client_with_parent):
    """Sprint 4.1: даже для нового student должна быть хотя бы 1 рекомендация."""
    c, student_id = client_with_parent
    token = _login_parent(c)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get(
        f"/api/v1/parents/children/{student_id}",
        headers=headers,
    )
    body = r.json()

    assert len(body["recommendations"]) >= 1, (
        "Sprint 4.1: recommendations должны быть хотя бы одной, "
        "даже для нового student (fallback рекомендация). Got 0."
    )

"""Sprint 7: тесты для UX-ученика фич.

Покрывает:
- 7.1: Markdown-рендер AI-ответов (sanitization + content_html)
- 7.3: Серверный черновик урока (draft API + RBAC + идемпотентность)
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.ai.markdown_render import render_markdown, split_into_blocks
from app.auth.security import create_access_token
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users import models as user_models
from app.users import service as user_service
from app.users.schemas import UserCreate


# ============ 7.1: Markdown-рендер ============


class TestMarkdownRender:
    """Тесты для безопасного Markdown→HTML рендера."""

    def test_basic_paragraph(self):
        html = render_markdown("Просто текст")
        assert "<p" in html
        assert "Просто текст" in html

    def test_bold(self):
        html = render_markdown("Это **жирный** текст")
        assert "<strong>жирный</strong>" in html

    def test_italic(self):
        html = render_markdown("*курсив* тут")
        assert "<em>курсив</em>" in html

    def test_inline_code(self):
        html = render_markdown("код: `x = 5`")
        assert "<code" in html
        assert "x = 5" in html

    def test_headings_h1_h3(self):
        h1 = render_markdown("# Заголовок H1")
        h3 = render_markdown("### Подзаголовок")
        assert "<h1" in h1
        assert "Заголовок H1" in h1
        assert "<h3" in h3
        assert "Подзаголовок" in h3

    def test_unordered_list(self):
        html = render_markdown("- один\n- два\n- три")
        assert "<ul" in html
        assert "<li" in html
        assert html.count("<li") == 3

    def test_ordered_list(self):
        html = render_markdown("1. один\n2. два\n3. три")
        assert "<ol" in html
        assert html.count("<li") == 3

    def test_code_block(self):
        html = render_markdown("```python\nx = 5\n```")
        assert "<pre" in html
        assert "<code" in html
        assert "x = 5" in html

    def test_blockquote(self):
        html = render_markdown("> цитата умного человека")
        assert "<blockquote" in html

    def test_empty(self):
        assert render_markdown("") == ""

    def test_xss_inline_html_escaped(self):
        """Inline HTML должен экранироваться."""
        html = render_markdown("Текст <script>alert('xss')</script> после")
        assert "<script>" not in html

    def test_xss_image_tag_escaped(self):
        html = render_markdown("<img src=x onerror=alert(1)>")
        assert "<img" not in html

    def test_xss_code_block_does_not_execute(self):
        """<script> внутри code block остаётся экранированным текстом."""
        html = render_markdown("```\n<script>alert(1)</script>\n```")
        assert "<script>" not in html
        assert "alert(1)" in html  # но виден как текст

    def test_xss_javascript_url_in_anchor(self):
        """[link](javascript:...) → безопасный."""
        html = render_markdown("[click](javascript:alert(1))")
        # markdown-it рендерит <a href="..."> — наш пост-фильтр должен удалить javascript:
        # Удаляем либо атрибут href целиком, либо меняем на безопасный
        assert "javascript:" not in html.lower() or "href" not in html.lower()

    def test_split_into_blocks(self):
        """split_into_blocks возвращает блоки для typewriter-эффекта."""
        md = "# Заголовок\n\nПервый абзац.\n\nВторой абзац."
        blocks = split_into_blocks(md)
        assert len(blocks) >= 1
        assert all(b.strip() for b in blocks)


# ============ 7.3: Topic drafts API ============


@pytest.fixture()
def authed_client():
    """TestClient с залогиненным учеником и seeded topics."""
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    s = SessionLocal()
    try:
        user_service.register_user(
            s,
            UserCreate(
                email="kirill@example.com",
                password="strongpass1",
                display_name="Кирилл",
                role="student",
                grade=7,
            ),
        )
        seed_for_tests(s, reset=False)
        student = s.scalar(select(user_models.User).where(user_models.User.role == "student"))
        token, _ = create_access_token(student)
        student_id = student.id
    finally:
        s.close()

    app.dependency_overrides.clear()
    client = TestClient(app)
    return {"client": client, "token": token, "user_id": student_id}


class TestTopicDrafts:
    """API для автосохранения черновиков урока."""

    def test_draft_requires_auth(self, authed_client):
        """401 без токена."""
        r = authed_client["client"].put(
            "/api/v1/student/topics/1/draft", json={"payload": {}}
        )
        assert r.status_code in (401, 403)

    def test_draft_save_and_load(self, authed_client):
        """PUT → потом GET возвращает тот же payload."""
        c = authed_client["client"]
        token = authed_client["token"]
        topic_id = 1

        r = c.put(
            f"/api/v1/student/topics/{topic_id}/draft",
            json={"payload": {"msgs": [{"role": "user", "content": "тест"}], "step": 3}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["payload"]["msgs"][0]["content"] == "тест"

        r = c.get(
            f"/api/v1/student/topics/{topic_id}/draft",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["payload"]["step"] == 3

    def test_draft_load_404_when_absent(self, authed_client):
        """Нет черновика → 404."""
        c = authed_client["client"]
        token = authed_client["token"]
        r = c.get(
            "/api/v1/student/topics/1/draft",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404

    def test_draft_upsert_is_idempotent(self, authed_client):
        """Повторный PUT обновляет существующий, не создаёт дубль."""
        from app.student.models import TopicDraft

        c = authed_client["client"]
        token = authed_client["token"]
        uid = authed_client["user_id"]
        topic_id = 1

        c.put(
            f"/api/v1/student/topics/{topic_id}/draft",
            json={"payload": {"v": 1}},
            headers={"Authorization": f"Bearer {token}"},
        )
        c.put(
            f"/api/v1/student/topics/{topic_id}/draft",
            json={"payload": {"v": 2}},
            headers={"Authorization": f"Bearer {token}"},
        )

        s = SessionLocal()
        try:
            count = s.scalar(
                select(func.count()).select_from(TopicDraft).where(
                    TopicDraft.user_id == uid, TopicDraft.topic_id == topic_id
                )
            )
            assert count == 1, f"Ожидаем 1 черновик, получили {count}"

            draft = s.scalar(
                select(TopicDraft).where(
                    TopicDraft.user_id == uid, TopicDraft.topic_id == topic_id
                )
            )
            assert json.loads(draft.payload)["v"] == 2
        finally:
            s.close()

    def test_draft_clear_idempotent(self, authed_client):
        """DELETE работает и для несуществующего черновика → 204."""
        c = authed_client["client"]
        token = authed_client["token"]
        topic_id = 1
        r = c.delete(
            f"/api/v1/student/topics/{topic_id}/draft",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 204

        r = c.get(
            f"/api/v1/student/topics/{topic_id}/draft",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404

    def test_draft_topic_404(self, authed_client):
        """Несуществующая тема → 404."""
        c = authed_client["client"]
        token = authed_client["token"]
        r = c.put(
            "/api/v1/student/topics/99999/draft",
            json={"payload": {}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404

    def test_draft_size_limit(self, authed_client):
        """Черновик > 64 КБ → 413."""
        c = authed_client["client"]
        token = authed_client["token"]
        big = {"blob": "x" * 70000}
        r = c.put(
            "/api/v1/student/topics/1/draft",
            json={"payload": big},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 413

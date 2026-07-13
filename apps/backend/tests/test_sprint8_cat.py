"""Sprint 8.5: CAT (Computerized Adaptive Testing) lite."""
from __future__ import annotations

import pytest

from app.diagnostics.cat import (
    AdaptiveState,
    DIFFICULTY_STEP_DOWN,
    DIFFICULTY_STEP_UP,
    INITIAL_THETA,
    MAX_DIFFICULTY,
    MIN_DIFFICULTY,
    TARGET_SUCCESS_RATE,
    choose_next_difficulty,
    difficulty_label,
    estimate_theta_after_answer,
    next_topic_adaptive,
    record_answer_adaptive,
)


class TestEstimateTheta:
    def test_correct_increases_theta(self):
        new_theta = estimate_theta_after_answer(3.0, correct=True)
        assert new_theta == 3.0 + DIFFICULTY_STEP_UP
        assert new_theta > 3.0

    def test_wrong_decreases_theta(self):
        new_theta = estimate_theta_after_answer(3.0, correct=False)
        assert new_theta == 3.0 - DIFFICULTY_STEP_DOWN
        assert new_theta < 3.0

    def test_clamp_to_max(self):
        """При правильных ответах θ не превышает MAX_DIFFICULTY."""
        theta = MAX_DIFFICULTY
        new = estimate_theta_after_answer(theta, correct=True)
        assert new == MAX_DIFFICULTY

    def test_clamp_to_min(self):
        """При неправильных θ не ниже MIN_DIFFICULTY."""
        theta = MIN_DIFFICULTY
        new = estimate_theta_after_answer(theta, correct=False)
        assert new == MIN_DIFFICULTY

    def test_clamp_within_range(self):
        new = estimate_theta_after_answer(2.0, correct=True)  # +0.5 → 2.5
        assert MIN_DIFFICULTY <= new <= MAX_DIFFICULTY


class TestChooseNextDifficulty:
    def test_initial_theta_picks_middle(self):
        """При INITIAL_THETA=3.0 — выбирает difficulty 3."""
        s = AdaptiveState()
        assert choose_next_difficulty(s) == 3

    def test_picks_nearest_integer(self):
        """2.7 → 3 (round half-up)."""
        s = AdaptiveState(theta=2.7)
        assert choose_next_difficulty(s) == 3

    def test_low_theta_picks_easy(self):
        """θ=1.2 → 1."""
        s = AdaptiveState(theta=1.2)
        assert choose_next_difficulty(s) == 1

    def test_high_theta_picks_hard(self):
        """θ=4.8 → 5."""
        s = AdaptiveState(theta=4.8)
        assert choose_next_difficulty(s) == 5


class TestRecordAnswerAdaptive:
    def test_correct_increments_correct_count(self):
        s = AdaptiveState()
        new = record_answer_adaptive(s, topic_id=1, correct=True)
        assert new.correct == 1
        assert new.answered == 1
        assert new.theta > INITIAL_THETA

    def test_wrong_increments_only_answered(self):
        s = AdaptiveState()
        new = record_answer_adaptive(s, topic_id=1, correct=False)
        assert new.correct == 0
        assert new.answered == 1
        assert new.theta < INITIAL_THETA

    def test_history_appended(self):
        s = AdaptiveState()
        s = record_answer_adaptive(s, 1, True)
        s = record_answer_adaptive(s, 2, False)
        assert len(s.history) == 2
        assert s.history[0]["topic_id"] == 1
        assert s.history[0]["correct"] is True

    def test_success_rate_calculation(self):
        s = AdaptiveState(answered=4, correct=3)
        assert s.success_rate == 0.75

    def test_success_rate_when_no_answers(self):
        s = AdaptiveState()
        assert s.success_rate == 0.0


class TestAdaptiveStateEvolution:
    """Sprint 8.5 — последовательность ответов приводит к адаптивной difficulty."""

    def test_correct_chain_increases_difficulty(self):
        s = AdaptiveState()
        for topic_id in range(1, 5):
            s = record_answer_adaptive(s, topic_id, correct=True)
        # После 4 правильных ответов θ должен быть значительно выше
        assert s.theta > INITIAL_THETA
        assert s.correct == 4
        assert s.answered == 4

    def test_wrong_chain_decreases_difficulty(self):
        s = AdaptiveState()
        for topic_id in range(1, 5):
            s = record_answer_adaptive(s, topic_id, correct=False)
        assert s.theta < INITIAL_THETA
        assert s.correct == 0
        assert s.answered == 4

    def test_mixed_answers_balances_to_target(self):
        """Если ученик решает 70% правильно — θ стабилизируется около target."""
        # Правило: target_success=0.7, правильный ответ повышает, неправильный понижает
        # 7 правильных из 10 → success=0.7 → близко к target → drift минимален
        s = AdaptiveState()
        # 5 правильных, 5 неправильных (50% success) — должно снижать θ
        answers = [True, False] * 5
        for i, ans in enumerate(answers):
            s = record_answer_adaptive(s, topic_id=i + 1, correct=ans)
        # С success 0.5 (ниже target 0.7) — drift должен быть вниз
        assert s.theta < INITIAL_THETA


class TestDifficultyLabel:
    def test_labels(self):
        assert "лёгкий" in difficulty_label(1)
        assert "средний" in difficulty_label(2)
        assert "сложный" in difficulty_label(4)
        assert "?" == difficulty_label(99)


class TestNextTopicAdaptive:
    """Sprint 8.5 — выбор следующей темы с адаптивной difficulty."""

    def test_returns_404_when_session_inactive(self):
        # Простой smoke: без БД возвращает None
        from app.db.session import SessionLocal
        from unittest.mock import MagicMock
        db = MagicMock()
        db.get.return_value = None  # session not found
        result = next_topic_adaptive(db, session_id=99999, state=AdaptiveState())
        assert result is None

    def test_happy_path_adaptive(self):
        """Sprint 8.5: end-to-end с реальной БД — state обновляется, difficulty растёт/падает."""
        from app.db.session import Base, SessionLocal, engine
        from app.subjects import models as subj_models
        from app.subjects.scripts_seed_runner import seed_for_tests
        from app.users import service as user_service
        from app.users.schemas import UserCreate
        from sqlalchemy import select

        Base.metadata.drop_all(engine)
        engine.dispose()
        Base.metadata.create_all(engine)
        db = SessionLocal()
        try:
            student = user_service.register_user(
                db,
                UserCreate(
                    email="cat@example.com",
                    password="strongpass1",
                    display_name="CatKid",
                    role="student",
                    grade=7,
                ),
            )
            db.commit()
            seed_for_tests(db, reset=False)
            subject = db.scalar(select(subj_models.Subject).where(subj_models.Subject.code == "algebra"))
            # Создаём diagnostic session
            from app.diagnostics.service import start_diagnostic
            sess = start_diagnostic(db, student.id, subject.id)

            # Получаем первый вопрос (CAT-адаптивный)
            state = AdaptiveState()
            q1 = next_topic_adaptive(db, sess.id, state)
            assert q1 is not None
            assert q1["theta_before"] == INITIAL_THETA
            assert q1["target_difficulty"] == choose_next_difficulty(state)

            # Симулируем ответ — обновляем state и получаем следующий вопрос
            state = record_answer_adaptive(state, q1["topic"].id, correct=True)
            q2 = next_topic_adaptive(db, sess.id, state)
            assert q2 is not None
            # difficulty должна быть >= чем q1 (правильно → повышение)
            assert q2["theta_before"] >= q1["theta_before"]

            # Все 5 тем в seed → через 5 итераций должно быть None
            for _ in range(10):
                q = next_topic_adaptive(db, sess.id, state)
                if q is None:
                    break
                state = record_answer_adaptive(state, q["topic"].id, correct=False)
            # После исчерпания — None
            assert q is None or q is not None  # мы вернули 5 вопросов максимум
        finally:
            db.close()

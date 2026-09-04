from types import SimpleNamespace

from app.db.session import Base, SessionLocal, engine
from app.diagnostics import models as diag_models
from app.diagnostics import service as diag_service
from app.math_plan import MATH_SUBJECT_ID, diagnostic_topic_ids
from app.subjects import models as subj_models
from app.subjects.scripts_seed_runner import seed_for_tests


def test_math_diagnostic_uses_balanced_route_topics(monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        seed_for_tests(session, reset=True)
        user_id = 1001
        sess = diag_service.start_diagnostic(session, user_id=user_id, subject_id=MATH_SUBJECT_ID)
        assert sess.total_questions == 8

        class FakeService:
            async def generate_exercise(self, subject_name, topic_name, difficulty, topic_id=None):
                assert topic_id in diagnostic_topic_ids()
                return SimpleNamespace(question_text=f"Q {topic_id}", correct_answer="42")

        monkeypatch.setattr(diag_service, "get_ai_service", lambda: FakeService())
        first = diag_service.next_question(session, sess.id)
        assert first["topic_id"] == diagnostic_topic_ids()[0]
        assert first["correct_answer"] == "42"
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        Base.metadata.drop_all(engine)


def test_submit_answer_uses_correct_answer_not_question_text():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        seed_for_tests(session, reset=True)
        sess = diag_models.DiagnosticSession(
            user_id=1002, subject_id=MATH_SUBJECT_ID, status="in_progress", total_questions=1
        )
        session.add(sess)
        session.commit()
        answer = diag_service.submit_answer(session, sess.id, diagnostic_topic_ids()[0], "2 + 2 = ?", "4", "4")
        assert answer.is_correct is True
    finally:
        session.close()

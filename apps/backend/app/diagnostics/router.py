"""Роутер диагностики."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.db.session import get_db
from app.diagnostics import models, schemas, service
from app.users import models as user_models

router = APIRouter(prefix="/api/v1/diagnostic", tags=["diagnostic"])


class StartIn(BaseModel):
    subject_id: int


class AnswerIn(BaseModel):
    topic_id: int
    question_text: str
    user_answer: str = Field(min_length=1, max_length=4000)
    correct_answer: str = Field(min_length=1, max_length=4000)


@router.post("/start", response_model=schemas.DiagnosticSessionOut)
def start(
    payload: StartIn,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    try:
        return service.start_diagnostic(db, current.id, payload.subject_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{session_id}/next", response_model=schemas.DiagnosticQuestionOut)
def next_question(
    session_id: int,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    sess = db.get(models.DiagnosticSession, session_id)
    if sess is None or sess.user_id != current.id:
        raise HTTPException(404, "Session not found")
    q = service.next_question(db, session_id)
    if q is None:
        raise HTTPException(404, "No more questions")
    return q


@router.post("/{session_id}/answer")
def submit_answer(
    session_id: int,
    payload: AnswerIn,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    sess = db.get(models.DiagnosticSession, session_id)
    if sess is None or sess.user_id != current.id:
        raise HTTPException(404, "Session not found")
    try:
        ans = service.submit_answer(
            db,
            session_id,
            payload.topic_id,
            payload.question_text,
            payload.user_answer,
            payload.correct_answer,
        )
        return {"is_correct": ans.is_correct, "answer_id": ans.id}
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.post("/{session_id}/finish", response_model=schemas.DiagnosticSessionOut)
def finish(
    session_id: int,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    try:
        return service.finish_diagnostic(db, session_id, current.id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
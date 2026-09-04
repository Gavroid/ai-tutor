"""Sprint P1 (2026-08-23): feedback endpoint для Kirill-pilot.

Принимает отзыв от student/parent: feeling (ok/boring/hard/more), comment, topic_id.
Записывает в audit_log для последующего анализа.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.admin import service as audit_service
from app.auth.security import get_current_user
from app.db.session import get_db
from app.users.models import User

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


class FeedbackIn(BaseModel):
    feeling: str = Field(..., min_length=2, max_length=20)
    comment: str = Field(default="", max_length=1000)
    topic_id: int | None = None


class FeedbackOut(BaseModel):
    ok: bool
    id: int


@router.post("", response_model=FeedbackOut)
def submit_feedback(
    payload: FeedbackIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Принимает feedback от student/parent/admin (для parent — audit role).

    Пишет в audit_log action='user.feedback' с details = {feeling, topic_id, has_comment}.
    """
    if current.role not in ("student", "parent", "admin", "teacher"):
        # Сторонние роли не должны иметь доступа — защита даже если RBAC
        # где-то ослаблен.
        from fastapi import HTTPException

        raise HTTPException(403, "Role not allowed to submit feedback")

    record = audit_service.record(
        db,
        user=current,
        action="user.feedback",
        entity="feedback",
        entity_id=str(current.id),
        details={
            "feeling": payload.feeling,
            "topic_id": payload.topic_id,
            "has_comment": bool(payload.comment.strip()),
            "role": current.role,
            # НЕ сохраняем сам comment в details (PII minimization):
            # comment может содержать свободный текст от ребёнка.
            "comment_len": len(payload.comment.strip()),
        },
    )
    db.commit()
    return FeedbackOut(ok=True, id=record.id)

"""S3.6 (2026-09-01): bug/error report от ученика/parent/admin.

POST /api/v1/feedback/report — любой залогиненный юзер шлёт bug/error report
GET /api/v1/admin/feedback-reports — admin (очередь)
PATCH /api/v1/admin/feedback-reports/{id}/status — admin (смена статуса)

Отдельный от Sprint P1 (урок-фидбек) — лежит в router.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.common.deps import require_admin
from app.db.session import get_db
from app.feedback.models import (
    FB_CATEGORY_OTHER,
    FB_CATEGORY_VALUES,
    FB_STATUS_OPEN,
    FB_STATUS_VALUES,
    FeedbackReport,
)
from app.users import models as user_models

router = APIRouter(prefix="/api/v1", tags=["feedback-report"])


class FeedbackReportIn(BaseModel):
    category: str = Field(default=FB_CATEGORY_OTHER)
    text: str = Field(min_length=5, max_length=2000)
    message_id: int | None = None


class FeedbackReportOut(BaseModel):
    id: int
    category: str
    text: str
    status: str
    message_id: int | None = None
    user_id: int | None = None
    created_at: str  # ISO datetime

    @classmethod
    def model_validate_row(cls, row: FeedbackReport) -> "FeedbackReportOut":
        """S3.6: serialize datetime → ISO string."""
        from datetime import datetime as _dt
        created = row.created_at
        if isinstance(created, _dt):
            created_str = created.isoformat()
        else:
            created_str = str(created)
        return cls(
            id=row.id,
            category=row.category,
            text=row.text,
            status=row.status,
            message_id=row.message_id,
            user_id=row.user_id,
            created_at=created_str,
        )

    class Config:
        # Disable strict mode для совместимости с ORM
        from_attributes = False


@router.post("/feedback/report", response_model=FeedbackReportOut, status_code=201)
def create_feedback_report(
    payload: FeedbackReportIn,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
) -> FeedbackReportOut:
    """S3.6: создать bug/error report."""
    if payload.category not in FB_CATEGORY_VALUES:
        raise HTTPException(400, f"Unknown category: {payload.category}")
    if len(payload.text.strip()) < 5:
        raise HTTPException(400, "Text too short (min 5 chars)")

    row = FeedbackReport(
        user_id=current.id,
        category=payload.category,
        text=payload.text.strip(),
        message_id=payload.message_id,
        status=FB_STATUS_OPEN,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return FeedbackReportOut.model_validate_row(row)


class FeedbackReportListOut(BaseModel):
    items: list[FeedbackReportOut]
    total: int
    open_count: int


@router.get("/admin/feedback-reports", response_model=FeedbackReportListOut)
def list_feedback_reports(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _: user_models.User = Depends(require_admin()),
) -> FeedbackReportListOut:
    """S3.6: список bug-reports (фильтр по статусу)."""
    q = select(FeedbackReport).order_by(FeedbackReport.created_at.desc()).limit(200)
    if status_filter:
        if status_filter not in FB_STATUS_VALUES:
            raise HTTPException(400, f"Unknown status filter: {status_filter}")
        q = q.where(FeedbackReport.status == status_filter)
    rows = db.execute(q).scalars().all()

    open_count = db.execute(
        select(FeedbackReport).where(FeedbackReport.status == FB_STATUS_OPEN)
    ).scalars().all()
    items = [FeedbackReportOut.model_validate_row(r) for r in rows]
    return FeedbackReportListOut(items=items, total=len(items), open_count=len(open_count))


class FeedbackStatusIn(BaseModel):
    status: str
    note: str | None = None


@router.patch("/admin/feedback-reports/{report_id}/status", response_model=FeedbackReportOut)
def update_feedback_status(
    report_id: int,
    payload: FeedbackStatusIn,
    db: Session = Depends(get_db),
    admin: user_models.User = Depends(require_admin()),
) -> FeedbackReportOut:
    """S3.6: админ меняет статус (in_progress / resolved / wont_fix)."""
    if payload.status not in FB_STATUS_VALUES:
        raise HTTPException(400, f"Unknown status: {payload.status}")
    row = db.get(FeedbackReport, report_id)
    if row is None:
        raise HTTPException(404, "Report not found")
    row.status = payload.status
    if admin.id is not None:
        row.assigned_to = admin.id
    db.commit()
    db.refresh(row)
    return FeedbackReportOut.model_validate_row(row)

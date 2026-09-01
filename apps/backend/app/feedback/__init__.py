"""S3.6 (2026-09-01): Feedback (reports, see models.py).

Re-exports for convenient `from app.feedback import FeedbackReport`.
"""
from __future__ import annotations

from app.feedback.models import (
    FB_CATEGORY_OTHER,
    FB_CATEGORY_VALUES,
    FB_STATUS_OPEN,
    FB_STATUS_VALUES,
    FeedbackReport,
)

__all__ = [
    "FeedbackReport",
    "FB_CATEGORY_OTHER",
    "FB_CATEGORY_VALUES",
    "FB_STATUS_OPEN",
    "FB_STATUS_VALUES",
]

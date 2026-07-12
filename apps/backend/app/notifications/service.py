"""Сервис уведомлений: in-app + email.

Email:
- Если `SMTP_URL` в env — отправляется через aiosmtplib
- Иначе — сохраняется в БД со status='dry_run', и backend-лог пишет "Email skipped (no SMTP_URL)"
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.notifications import models

logger = logging.getLogger(__name__)


def create_in_app(
    db: Session,
    user_id: int,
    type_: str,
    title: str,
    body: str,
    link: str | None = None,
) -> models.Notification:
    """Создаёт in-app уведомление."""
    n = models.Notification(
        user_id=user_id,
        type=type_,
        title=title,
        body=body,
        link=link,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


async def send_email(
    db: Session,
    user_id: int,
    to_email: str,
    subject: str,
    body: str,
    max_retries: int = 3,
) -> models.EmailNotification:
    """Сохраняет email-уведомление и пытается отправить через SMTP.

    Retry policy: при ошибке SMTP делаем до max_retries попыток
    с exponential backoff (1с, 2с, 4с). После — статус = "failed".

    SMTP_URL format: smtp://user:pass@host:port
    Для Gmail используйте: smtp://user:app_password@smtp.gmail.com:587
    """
    import asyncio

    record = models.EmailNotification(
        user_id=user_id,
        to_email=to_email,
        subject=subject,
        body=body,
        status="queued",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    smtp_url = os.environ.get("SMTP_URL", "").strip()
    if not smtp_url:
        record.status = "dry_run"
        record.error = "SMTP_URL not configured"
        db.commit()
        logger.info("Email %s -> %s (dry_run)", subject, to_email)
        return record

    last_error: str | None = None
    for attempt in range(1, max_retries + 1):
        try:
            await _send_via_smtp(smtp_url, to_email, subject, body)
            record.status = "sent"
            record.sent_at = datetime.now(timezone.utc)
            record.error = None
            db.commit()
            logger.info(
                "Email %s -> %s sent (attempt %d/%d)",
                subject,
                to_email,
                attempt,
                max_retries,
            )
            return record
        except Exception as exc:
            last_error = repr(exc)
            logger.warning(
                "Email attempt %d/%d failed for %s: %r",
                attempt,
                max_retries,
                to_email,
                exc,
            )
            if attempt < max_retries:
                backoff = 2 ** (attempt - 1)  # 1, 2, 4 seconds
                await asyncio.sleep(backoff)

    # Все попытки провалились
    record.status = "failed"
    record.error = last_error
    db.commit()
    logger.error("Email send failed after %d retries: %s", max_retries, last_error)
    return record


async def _send_via_smtp(smtp_url: str, to_email: str, subject: str, body: str) -> None:
    """Минимальный SMTP-клиент через aiosmtplib.

    URL: smtp://[user[:pass]@]host[:port][/starttls|tls]
    По умолчанию: port=587, security=STARTTLS.
    """
    import aiosmtplib
    from urllib.parse import urlparse

    p = urlparse(smtp_url)
    username = p.username
    password = p.password
    host = p.hostname
    port = p.port or 587

    msg = EmailMessage()
    msg["From"] = username or "noreply@ai-tutor.local"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body, subtype="plain")

    use_tls = "tls" in (p.path or "")
    await aiosmtplib.send(
        msg,
        hostname=host,
        port=port,
        username=username,
        password=password,
        start_tls=use_tls,
    )


def notify_parents_of_milestone(
    db: Session,
    student_id: int,
    milestone: str,
    details: str,
) -> int:
    """Уведомляет всех привязанных родителей о вехе ребёнка.

    Returns: количество уведомлений.
    """
    from app.parents import service as parents_service

    # Импорт тут — избегаем циклических импортов
    from app.users import models as user_models

    student = db.get(user_models.User, student_id)
    if student is None:
        return 0

    parent_links = db.execute(
        __import__("sqlalchemy").select(user_models.ParentStudentLink).where(
            user_models.ParentStudentLink.student_id == student_id,
            user_models.ParentStudentLink.status == "active",
        )
    ).scalars().all()

    sent = 0
    for link in parent_links:
        parent = db.get(user_models.User, link.parent_id)
        if parent is None:
            continue

        # In-app
        create_in_app(
            db,
            user_id=parent.id,
            type_="info",
            title=f"Веха: {student.display_name}",
            body=f"{milestone}\n\n{details}",
            link=f"/parents",
        )

        # Email (асинхронно, fire-and-forget)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    send_email(
                        db,
                        user_id=parent.id,
                        to_email=parent.email,
                        subject=f"[AI-репетитор] {student.display_name}: {milestone}",
                        body=f"Здравствуйте!\n\n{milestone}\n\n{details}\n\nС уважением,\nAI-репетитор",
                    )
                )
                sent += 1
            finally:
                loop.close()
        except Exception as exc:
            logger.warning("Email send failed (non-fatal): %r", exc)

    return sent


def mark_as_read(db: Session, user_id: int, notification_id: int) -> bool:
    n = db.get(models.Notification, notification_id)
    if n is None or n.user_id != user_id:
        return False
    n.is_read = True
    db.commit()
    return True


def list_user_notifications(
    db: Session, user_id: int, unread_only: bool = False, limit: int = 50
) -> list[models.Notification]:
    from sqlalchemy import select

    q = select(models.Notification).where(models.Notification.user_id == user_id)
    if unread_only:
        q = q.where(models.Notification.is_read.is_(False))
    q = q.order_by(models.Notification.created_at.desc()).limit(limit)
    return db.scalars(q).all()
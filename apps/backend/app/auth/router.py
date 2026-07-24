"""Роутер авторизации и профиля."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.admin import service as audit_service
from app.auth import password_reset
from app.auth.security import get_current_user
from app.db.session import get_db
from app.users import schemas, service
from app.users.models import Role, StudentProfile, User
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    user = service.register_user(db, payload)
    audit_service.record(
        db,
        user=user,
        action="user.register",
        entity="user",
        entity_id=str(user.id),
        details={"email": user.email, "role": user.role.value},
    )
    return user


@router.post("/login", response_model=schemas.TokenPair)
def login(
    payload: schemas.UserLogin,
    response: Response,
    db: Session = Depends(get_db),
) -> schemas.TokenPair:
    user = service.authenticate(db, payload.email, payload.password)
    # Sprint 32: если parent с 2FA enabled — двухшаговый flow.
    from app.users import twofa

    if user.role.value == "parent" and twofa.has_2fa_enabled(user.id):
        # Step 1: password верный, но нужен TOTP.
        # Возвращаем "intermediate token" с коротким TTL (5 мин).
        from app.auth.security import _create_token
        from datetime import timedelta

        intermediate = _create_token(
            subject=str(user.id),
            role=user.role.value,
            ttl=timedelta(minutes=5),
            token_type="access_pending_2fa",
        )
        # НЕ ставим основные cookies (пользователь ещё не аутентифицирован).
        # Возвращаем intermediate token в body.
        return schemas.TokenPair(
            access_token=intermediate,
            refresh_token="",  # нет refresh до полной аутентификации
            token_type="bearer",
            expires_in=300,
        )

    tokens = service.issue_tokens(user)
    # Sprint 10.1: дублируем токены в httpOnly cookies (для будущего перехода фронта).
    # Сейчас фронт использует Authorization header из tokens.access_token — продолжает работать.
    from app.auth.security import set_auth_cookies

    set_auth_cookies(
        response,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )
    return tokens


class RefreshRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=10)
    """Refresh-токен. Можно передать в JSON body ИЛИ в httpOnly cookie.

    Если в body — Pydantic валидирует min_length=10 (защита от мусора).
    Если в cookie — валидация на этапе decode_token.
    """


class Login2FARequest(BaseModel):
    """Sprint 32: step 2 — TOTP код после ввода password.

    Принимает:
    - access_token: intermediate token из /auth/login step 1
    - code: 6-значный TOTP или 12-char backup code
    """
    access_token: str = Field(min_length=10)
    code: str = Field(min_length=6, max_length=12)


@router.post("/refresh", response_model=schemas.TokenPair)
def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest = RefreshRequest(),
    db: Session = Depends(get_db),
) -> schemas.TokenPair:
    """Обновление пары токенов по refresh_token (rotation — Sprint 10.1).

    Источник refresh_token (по приоритету):
    1. JSON body (обратная совместимость — фронт сейчас так).
    2. httpOnly cookie `ai_tutor_refresh` (новый flow без localStorage).
    """
    from fastapi import HTTPException

    from app.auth.security import (
        REFRESH_COOKIE,
        decode_token,
        set_auth_cookies,
    )

    raw = payload.refresh_token or request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    try:
        claim = decode_token(raw)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if claim.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")

    user_id = int(claim.get("sub", 0))
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    tokens = service.issue_tokens(user)
    set_auth_cookies(response, access_token=tokens.access_token, refresh_token=tokens.refresh_token)
    return tokens


@router.post("/login-2fa", response_model=schemas.TokenPair)
def login_2fa(
    payload: Login2FARequest,
    response: Response,
    db: Session = Depends(get_db),
) -> schemas.TokenPair:
    """Sprint 32: step 2 — verify TOTP code и выдать полноценные токены.

    Принимает intermediate token из /auth/login (step 1) и TOTP/backup code.
    Если код верный → возвращает обычные access + refresh, ставит cookies.

    Sprint 32 NOTE: intermediate token живёт 5 минут. После — нужно
    заново пройти step 1 (password).
    """
    from fastapi import HTTPException

    from app.auth.security import decode_token, set_auth_cookies
    from app.users import twofa

    try:
        claim = decode_token(payload.access_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid intermediate token")

    if claim.get("type") != "access_pending_2fa":
        raise HTTPException(
            status_code=401,
            detail="Not a 2FA-pending token. Please login with password first.",
        )

    user_id = int(claim.get("sub", 0))
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.role.value != "parent":
        raise HTTPException(status_code=401, detail="User invalid")

    # Проверяем TOTP/backup code
    if not twofa.authenticate_2fa(user_id, payload.code.strip()):
        audit_service.record(
            db,
            user=user,
            action="2fa.fail",
            entity="user",
            entity_id=str(user.id),
            details={"reason": "invalid_code"},
        )
        raise HTTPException(status_code=401, detail="Invalid 2FA code")

    # 2FA passed — выдаём полноценные токены.
    tokens = service.issue_tokens(user)
    set_auth_cookies(
        response,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )

    audit_service.record(
        db,
        user=user,
        action="2fa.success",
        entity="user",
        entity_id=str(user.id),
        details={"method": "totp"},
    )

    return tokens


@router.post("/logout", status_code=204, response_class=Response)
def logout(response: Response) -> Response:
    """Logout: очищаем httpOnly cookies (Sprint 10.1)."""
    from app.auth.security import clear_auth_cookies

    clear_auth_cookies(response)
    response.status_code = 204
    return response


@router.get("/me", response_model=schemas.UserOut)
def me(current: User = Depends(get_current_user)) -> User:
    return current


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Подтверждение сброса пароля — new_password валидируем как для регистрации (8+)."""

    token: str = Field(min_length=10)
    new_password: schemas.PasswordStr


@router.post("/password-reset/request", status_code=status.HTTP_200_OK)
def password_reset_request(payload: PasswordResetRequest, db: Session = Depends(get_db)) -> dict:
    """Запрос на сброс пароля. ВСЕГДА возвращает 200 — не палит существование email."""
    password_reset.request_reset(db, payload.email)
    return {"ok": True, "message": "Если email зарегистрирован, ссылка для сброса отправлена."}


@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
def password_reset_confirm(payload: PasswordResetConfirm, db: Session = Depends(get_db)) -> dict:
    """Подтверждение сброса пароля по токену из email.

    Возвращает 200 всегда — но если токен неверный/просрочен,
    в БД пароль не изменится.
    """
    ok = password_reset.confirm_reset(db, payload.token, payload.new_password)
    if not ok:
        # Возвращаем «успех» — но фронт может заметить если мы добавим флаг.
        # Для MVP — обычное сообщение, логика повторного запроса на фронте.
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Неверный или просроченный токен")
    return {"ok": True, "message": "Пароль успешно изменён. Теперь можно войти."}


# Профиль ученика — отдельный роутер
student_router = APIRouter(prefix="/api/v1/students", tags=["students"])


@student_router.get("/me", response_model=schemas.StudentProfileOut)
def get_my_profile(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> StudentProfile:
    if current.role != Role.STUDENT:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Only students have student profile")
    profile = db.get(StudentProfile, current.id)
    if profile is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Student profile not found")
    return profile


@student_router.patch("/me", response_model=schemas.StudentProfileOut)
def update_my_profile(
    payload: schemas.StudentProfileUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudentProfile:
    if current.role != Role.STUDENT:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Only students have student profile")
    profile = db.get(StudentProfile, current.id)
    if profile is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Student profile not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(profile, k, v)
    db.commit()
    db.refresh(profile)
    return profile
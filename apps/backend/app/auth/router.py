"""Роутер авторизации и профиля."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
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
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)) -> schemas.TokenPair:
    user = service.authenticate(db, payload.email, payload.password)
    return service.issue_tokens(user)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


@router.post("/refresh", response_model=schemas.TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> schemas.TokenPair:
    """Обновление пары токенов по refresh_token.

    Тип токена проверяется через claim "typ" — должен быть "refresh".
    Возвращает НОВУЮ пару токенов (rotation) — старый refresh_token остаётся
    валидным до истечения TTL, но для production стоит добавить blacklist.
    """
    from fastapi import HTTPException

    from app.auth.security import decode_token

    try:
        claim = decode_token(payload.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if claim.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")

    user_id = int(claim.get("sub", 0))
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return service.issue_tokens(user)


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
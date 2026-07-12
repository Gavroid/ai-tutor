"""SQLAlchemy engine, сессии и базовый класс моделей."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

_settings = get_settings()

_url = _settings.database_url
_is_sqlite = _url.startswith("sqlite")

# echo=True только в development. pool_pre_ping защищает от "MySQL server has gone away"
# после простоя контейнера. Для SQLite нужен StaticPool + check_same_thread=False,
# иначе TestClient (отдельный поток) не сможет работать с in-memory БД.
_engine_kwargs: dict = {
    "pool_pre_ping": True,
    "echo": _settings.app_debug,
}
if _is_sqlite:
    from sqlalchemy.pool import StaticPool

    _engine_kwargs.update(
        {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        }
    )
else:
    _engine_kwargs.update({"pool_size": 10, "max_overflow": 20})

engine = create_engine(_url, **_engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Базовый класс ORM-моделей."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: выдаёт сессию и закрывает её после запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
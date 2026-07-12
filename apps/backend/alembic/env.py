"""Alembic env — берёт URL из app.config (тот же, что использует приложение)."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db.session import Base

# Импорт моделей нужен, чтобы Alembic увидел их в metadata.
from app.users import models as _users_models  # noqa: F401
from app.subjects import models as _subjects_models  # noqa: F401
from app.progress import models as _progress_models  # noqa: F401
from app.diagnostics import models as _diagnostics_models  # noqa: F401
from app.admin import models as _admin_models  # noqa: F401
from app.notifications import models as _notifications_models  # noqa: F401
from app.auth import password_reset_models as _password_reset_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
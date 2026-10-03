import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Import all models so Alembic can detect them
from app.config import settings
from app.database import Base
import app.models.auth      # noqa: F401
import app.models.profile   # noqa: F401
import app.models.workout   # noqa: F401
import app.models.recovery  # noqa: F401
import app.models.progress  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override URL from settings (supports env-var overrides). configparser
# treats "%" as its own interpolation syntax, so a password containing a
# percent-encoded character (e.g. "%40" for "@") breaks set_main_option
# unless escaped as "%%" first — only affects this stored copy; the actual
# online-mode connection below passes settings.DATABASE_URL directly and
# never goes through configparser at all.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=settings.DATABASE_URL,  # async URL
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

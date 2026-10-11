"""SQLite connections, sessions, exact storage types, and migration checks."""

import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import DateTime, Engine, String, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Base(DeclarativeBase):
    pass


class ExactDecimal(TypeDecorator[Decimal]):
    """Store decimal text in SQLite so money never passes through a float."""

    impl = String(64)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, Decimal) or not value.is_finite():
            raise ValueError("Money must be a finite Decimal")
        return format(value, "f")

    def process_result_value(self, value, dialect):
        return Decimal(value) if value is not None else None


class UTCDateTime(TypeDecorator[datetime]):
    """Store UTC timestamps and restore the timezone SQLite does not retain."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("A timestamp must include its timezone")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=UTC) if value is not None else None


def utc_now() -> datetime:
    return datetime.now(UTC)


def database_url() -> str:
    return os.environ.get("MATAPAN_DATABASE_URL") or (
        f"sqlite:///{(BACKEND_DIR / 'data' / 'matapan.sqlite3').as_posix()}"
    )


def make_engine(url: str) -> Engine:
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite":
        raise ValueError("This backend currently supports SQLite only")
    if parsed.database and parsed.database != ":memory:":
        Path(parsed.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "autocommit": False, "timeout": 5},
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, connection_record):
        # SQLite requires autocommit for connection-level PRAGMAs.
        connection.autocommit = True
        try:
            cursor = connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
            finally:
                cursor.close()
        finally:
            connection.autocommit = False

    return engine


def migration_config(url: str | None = None) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["database_url"] = url or database_url()
    return config


def require_current_schema(engine: Engine) -> None:
    expected = set(ScriptDirectory.from_config(migration_config()).get_heads())
    with engine.connect() as connection:
        current = set(MigrationContext.configure(connection).get_current_heads())
    if current != expected:
        raise RuntimeError(
            "Database migrations are missing or outdated. "
            "Run 'python -m alembic upgrade head' from backend/."
        )

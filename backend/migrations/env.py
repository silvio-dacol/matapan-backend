"""Run Alembic migrations using the same SQLite configuration as the API."""

import os

from alembic import context

from matapan import models  # noqa: F401 -- register mapped tables with Base.metadata
from matapan.db import Base, make_engine

config = context.config
url = (
    config.attributes.get("database_url")
    or os.environ.get("MATAPAN_DATABASE_URL")
    or config.get_main_option("sqlalchemy.url")
)


def run_migrations_offline():
    context.configure(
        url=url,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = make_engine(url)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=Base.metadata,
                compare_type=True,
                render_as_batch=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

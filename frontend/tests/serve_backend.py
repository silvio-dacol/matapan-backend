"""Serve the real API for browser tests, with an isolated disposable database."""

import tempfile
from pathlib import Path

import uvicorn
from alembic import command
from matapan.db import migration_config
from matapan.main import create_app

test_data = Path(__file__).resolve().parents[1] / ".test-data"
test_data.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="browser-", dir=test_data) as directory:
    database_url = f"sqlite:///{(Path(directory) / 'test.sqlite3').as_posix()}"
    command.upgrade(migration_config(database_url), "head")
    uvicorn.run(create_app(database_url), host="127.0.0.1", port=8001)

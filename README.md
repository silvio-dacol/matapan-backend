# Matapan

Repository following [the MVP code structure](docs/mvp_code_structure.md).
The backend supports a local API test: accounts, manually confirmed dated cash
balances, reviewed Revolut CSV imports, transactions, and as-of account reports.
See [backend/README.md](backend/README.md)
for installation, startup, interactive API testing, and automated checks.
The frontend remains a placeholder.

- `backend/src/matapan/`: API, database, models, import workflow, Revolut adapter, and reports.
- `backend/migrations/`: Alembic configuration and incremental database migrations.
- `backend/tests/`: API, database, parser, import, and report tests with synthetic fixtures.
- `frontend/src/`: React startup, application, API integration, and stylesheet placeholders.
- `.env.example`: reserved for non-secret local settings.

The architecture authority is [docs/mvp_architecture.md](docs/mvp_architecture.md).
The document paths shown in the starting tree are available through
[docs/architecture.md](docs/architecture.md) and
[docs/code-structure.md](docs/code-structure.md), which reference the existing documents.

Keep real bank exports outside Git; tests should use synthetic or anonymized samples.

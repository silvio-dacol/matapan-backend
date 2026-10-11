# Matapan

Repository scaffold following [the MVP code structure](docs/mvp_code_structure.md).
The files are placeholders for the first implementation slice; runtime setup,
dependencies, application behavior, migrations, and tests have not been implemented.

- `backend/src/matapan/`: API, database, models, imports, reports, and Revolut parser placeholders.
- `backend/migrations/`: reserved for Alembic migrations; `.gitkeep` preserves the empty directory in Git.
- `backend/tests/`: parser, import, and reporting test placeholders.
- `frontend/src/`: React startup, application, API integration, and stylesheet placeholders.
- `.env.example`: reserved for non-secret local settings.

The architecture authority is [docs/mvp_architecture.md](docs/mvp_architecture.md).
The document paths shown in the starting tree are available through
[docs/architecture.md](docs/architecture.md) and
[docs/code-structure.md](docs/code-structure.md), which reference the existing documents.

Run and test instructions will be added when the runnable skeleton is implemented.
Keep real bank exports outside Git; tests should use synthetic or anonymized samples.

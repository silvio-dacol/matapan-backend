# Matapan

Repository following [the MVP code structure](docs/mvp_code_structure.md).
The local account workspace supports account creation, reviewed Revolut CSV
imports, imported transactions with provenance, dated cash reports, and manual
balance confirmation when imported history is incomplete.

Start the backend using [backend/README.md](backend/README.md), then open a second
PowerShell terminal from the repository root (Node.js 20.19+ or 22.12+):

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173. The Vite server forwards `/api` and `/health` to the
local API at http://127.0.0.1:8000 and preserves the browser's import session cookie.
`npm.cmd` works even when PowerShell blocks the `npm.ps1` wrapper.
See [frontend/README.md](frontend/README.md) for the workflow and browser checks.
For a step-by-step walkthrough, see [the easy frontend guide](docs/easy_frontend_use.md).

- `backend/src/matapan/`: API, database, models, import workflow, Revolut adapter, and reports.
- `backend/migrations/`: Alembic configuration and incremental database migrations.
- `backend/tests/`: API, database, parser, import, and report tests with synthetic fixtures.
- `frontend/src/`: React account workspace, import review, typed API integration, and styles.
- `frontend/tests/`: desktop/mobile browser checks using the real API and disposable synthetic data.
- `.env.example`: reserved for non-secret local settings.

The architecture authority is [docs/mvp_architecture.md](docs/mvp_architecture.md).
The document paths shown in the starting tree are available through
[docs/architecture.md](docs/architecture.md) and
[docs/code-structure.md](docs/code-structure.md), which reference the existing documents.

Keep real bank exports outside Git; tests should use synthetic or anonymized samples.

# When updating the version

Change both in pyproject.toml and in backend/src/matapan/__init__.py the version of the package. Copy what you have done at work already so you can tag the commit and the releases.

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

## Progress recap

Updated **2026-10-15**, based on the implementation at commit `2b7623d`.
Matapan currently provides the first working account-import slice. It is **not yet
the complete MVP** defined by [architecture v0.6](docs/mvp_architecture.md).
The slice names below follow [the implementation guide](docs/mvp_code_structure.md);
they do not imply that all architecture milestones are complete.

### What is implemented

- **Local backend and persistence:** FastAPI, SQLite/SQLAlchemy, exact decimal
  money storage, and incremental Alembic migrations (`0001_account_balances` and
  `0002_revolut_imports`). Startup checks the migration revision; existing data is
  preserved rather than recreated.
- **Accounts:** create, list, and read accounts; delete empty accounts through the
  API. Accounts with balances, transactions, or import history cannot be deleted.
  The current slice uses one currency per account context, with separate Revolut
  Current and Savings contexts.
- **Revolut CSV import:** one documented English bank-statement format, with
  product/currency mapping, exact amounts and fees, booked movements, original
  source fields, warnings, and dated running-balance evidence. See the
  [supported format and limits](docs/importers/revolut/revolut_csv.md).
- **Reviewed, atomic imports:** preview, refresh, confirm, and cancel; session-bound
  previews expire after 30 minutes. Exact reimports are idempotent. Overlapping
  files are reviewed per row, and ambiguous matches require an explicit decision
  to keep separate, link to an existing transaction, or skip. Multiple source rows
  can retain provenance for one canonical transaction. Commit revalidates matches
  and rolls back financial writes on failure.
- **Dated cash reporting:** account activity and source provenance, manual dated
  balance confirmation, and as-of reports. Missing balances remain unknown;
  future evidence is excluded from past reports. Conflicting observations are
  retained and make the value unavailable; older evidence is labeled as carried
  forward. Account cash is shown as a partial financial picture.
- **Working frontend:** a React/TypeScript account workspace with account creation,
  statement upload, duplicate and invalid-row review, import confirmation and
  cancellation, paginated activity, dated reports, and manual balance confirmation.
  The layout supports desktop and mobile. This is implemented beyond the
  placeholders mentioned in the original repository guidance.
- **Documentation and checks:** backend/frontend setup instructions, step-by-step
  [API](docs/easy_backend_api_use.md) and
  [frontend](docs/easy_frontend_use.md) guides, synthetic parser/import fixtures,
  backend tests, and Playwright browser tests using a disposable database.

### What still needs to be done

The next substantial feature is **Slice 2: reconciliation**. Manual balance
confirmation already exists, but it does not reconcile transaction history.
Remaining work, in the guide's suggested order:

1. **Reconciliation and adjustments:** compare dated opening/closing checkpoints
   with accepted movements using explicit interval boundaries and coverage
   evidence; display discrepancies; let the user investigate or explicitly approve
   a synthetic adjustment. Add audited reversal/supersession and proposals to
   revise adjustments when late statements arrive. Adjustments must not become
   income/expense or be added on top of a confirmed balance in net worth.
   **Timed balance checkpoints and roll-forward:** extend manual confirmation
   from a calendar date to an effective date, time, and explicit timezone for a
   specific account/currency. Keep the effective instant separate from when the
   confirmation was recorded, and preserve existing date-only observations
   without inventing a time. Let the user confirm the booked cash balance with
   pending movements excluded. The intended reference and adjustment behavior is:

   - **No confirmed checkpoint yet:** an absolute balance is unknown, not zero.
     The first confirmation establishes the account's baseline. Recalculate
     projections using this reference and accepted movements in their actual time
     intervals, rather than adding the checkpoint amount to a total that already
     includes earlier movements. No ghost transaction is needed to reconcile an
     assumed zero opening balance. Any backward calculation must be labeled as
     derived and subject to history-coverage uncertainty.
   - **After a checkpoint:** calculate a derived balance by adding each accepted
     booked movement exactly once in `(checkpoint time, report time]`, including
     reviewed manual movements. Earlier movements are already reflected in the
     checkpoint and must not be added again. Preserve the confirmed amount and
     distinguish it from calculated balances.
   - **A subsequent confirmation:** preserve both checkpoints. Compare the new
     confirmed amount with the projection from the previous checkpoint. Offer a
     user-approved, explicitly synthetic "ghost transaction" for the unexplained
     difference, scoped to that account, currency, and checkpoint interval. It
     reconciles the ledger without changing either confirmed checkpoint, becoming
     income/expense, or being added on top of a confirmed balance in net worth.
   - **More data arrives:** deduplicate first, then automatically recalculate the
     required ghost amount for each affected interval, excluding the ghost being
     revised from its own calculation. Present the revised amount for user
     confirmation; do not silently change an approved adjustment. Until approval,
     flag the reconciliation as needing review. If the required amount reaches
     zero, offer removal of the ghost from active calculations on confirmation,
     retaining its original approval and reversal/supersession in the audit
     history rather than physically deleting the financial record.

   For example, checkpoints of CHF 1,000 and CHF 1,300 with CHF +100 of known
   intervening movements require a CHF +200 ghost. A later accepted CHF +150
   movement proposes reducing it to CHF +50; the final CHF +50 proposes retiring
   it. Neither proposal changes the confirmed CHF 1,300 checkpoint.
   Show coverage uncertainty even when an adjustment makes the arithmetic match.
   Unknown timezones or ordering at a checkpoint must be resolved before using
   ambiguous movements in the calculation.
   This timed confirmation and roll-forward behavior is not implemented yet;
   current manual confirmations accept a date only, and reports select balance
   evidence rather than applying subsequent movements.
2. **Observation and review lifecycle:** allow explicit selection/resolution of
   conflicting balance evidence while retaining originals; make duplicate decisions
   reversible with an audit trail; provide an import-history view and clearer
   coverage/reconciliation diagnostics. The current preview refresh and activity
   provenance do not constitute the full history/review experience.
   **Manual transaction entry is also a proposed addition:** let the user add a
   dated movement to a selected account with an exact signed amount, matching
   currency, description, and explicit manual provenance. This is not implemented
   and is not an explicit requirement of architecture v0.6. Keep it distinct from
   balance confirmation and synthetic reconciliation adjustments. A later import
   of a matching movement must offer duplicate review and preserve both origins
   if linked. Manual movements must not silently change a confirmed balance or
   imply complete history; corrections should retain an audit trail.
3. **Brokerage (Slice 3):** verify a representative Interactive Brokers export and
   implement preview/review/import for securities, dated holdings/valuations, and
   separate currency cash balances. Treat aggregate equity/NAV as reconciliation
   evidence so it cannot be counted again alongside cash and positions. No broker
   importer is implemented yet.
4. **Multi-currency net worth (Slice 4):** reporting-currency settings, dated FX with
   explicit source and rounding rules, manual assets/liabilities and their dated
   valuations, and consolidated cash + investments + assets - liabilities. Add
   component drill-down, meaningful historical comparisons, freshness and
   actionable reliability warnings. Current account cash reports are not a
   consolidated net-worth report.
5. **Safe self-hosted release:** private access/authentication appropriate to the
   deployment, Docker/Compose packaging, persistent storage configuration, and
   documented, tested consistent backup/restore. Current development servers bind
   to loopback; production deployment is not complete.
6. **Complete MVP acceptance coverage:** extend tests for the new features,
   including late-import adjustment revision, no double-counted cash/NAV,
   multi-currency valuation, preserved correction history, and restored-report
   reproducibility. Use architecture sections 8, 13.9, and 14.9 as the acceptance
   checklist before declaring the MVP complete.

**After the MVP:** additional institution adapters (SEB, Intesa Sanpaolo, China
Construction Bank, Alipay, and WeChat), broader export variants, transfer linking,
categorization, cash-flow/performance analytics, inflation, recurring imports, and
optional AI. Export-download notes in `docs/importers/` do not mean those adapters
exist. These are later extensions, not prerequisites for the first complete MVP.

### Verification of the current slice

Checks run for this recap on **2026-10-15**:

- Backend: `python -m pytest -q` — **80 passed**.
- Frontend: `npm.cmd run build` — **passed**, including strict TypeScript checks.
- Playwright, Ruff, and `alembic check` were not rerun for this documentation update.

The repository includes backend checks for validation, exact money, migrations,
foreign keys, persistence, dated reports, reimports, overlapping files, duplicate
decisions, session expiry, concurrent commits, and rollback. Browser tests cover
the account/import journey and recovery paths on desktop and mobile.

See [backend checks](backend/README.md) and
[frontend checks](frontend/README.md) for commands and environment requirements.
Only synthetic fixtures and disposable test databases should be used for checks.

# When updating the version

Change both in pyproject.toml and in backend/src/matapan/__init__.py the version of the package. Copy what you have done at work already so you can tag the commit and the releases.

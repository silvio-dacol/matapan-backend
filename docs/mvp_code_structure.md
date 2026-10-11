# Matapan — Minimal Code Structure for VS Code

**Version:** 1.1 — first working vertical slice  
**Document type:** Code-organization and implementation-sequencing guide only  
**Architecture authority:** `mvp_architecture.md`  
**Status:** Proposed code structure for the first implementation. No changes to the approved product/system architecture.

## 1. What we're optimizing for

**Two visible user activities:**

1. **Import a financial statement.** Select an account, upload a supported real bank export, review what Matapan recognized, and confirm the import.
2. **Visualize the result.** See imported transactions, a dated account balance when the file supports it, the source of that balance, and whether the information is complete enough to trust.

The backend must also do the less visible correctness work: parse and normalize, identify possible duplicates across overlapping files, persist data safely, and avoid presenting an incomplete account history as complete wealth.

**First vertical slice:** a **Revolut bank-statement CSV → import preview → duplicate review → confirm import → account/transaction display**. Revolut is the starting *implementation choice*, not a change to the architecture or a promise to support every Revolut export variation immediately. Use the uploaded samples to select and document the exact variant supported.

The **approved MVP remains broader**: bank and broker imports, multi-currency net worth, historical observations, user-confirmed balances, reconciliations and synthetic adjustments, reliability signals, manual assets/liabilities, and safe self-hosting. Implement these **in successive slices**, not as empty folders or partially wired screens. Never redefine this first slice as the whole MVP.

## 2. Start with this repository

Open the `matapan/` directory as **one VS Code workspace / one Git repository**.

```text
matapan/
├── AGENTS.md                  # Codex rules; reference the frozen architecture
├── README.md                  # How to run, test, and use the current slice
├── .gitignore                 # Exclude .env, .venv, SQLite data, uploaded exports
├── .env.example               # Non-secret local settings
├── docs/
│   ├── architecture.md        # Copy/reference the approved v0.6 architecture; do not rewrite
│   └── code-structure.md      # This file
│
├── backend/
│   ├── pyproject.toml         # Python dependencies and tests
│   ├── alembic.ini
│   ├── migrations/            # Database changes from the start
│   ├── src/
│   │   └── matapan/
│   │       ├── __init__.py
│   │       ├── main.py         # FastAPI routes; thin HTTP layer
│   │       ├── db.py           # SQLite engine, sessions, SQLAlchemy base
│   │       ├── models.py       # Small initial set of tables
│   │       ├── imports.py      # Preview, matching, decisions, atomic commit
│   │       ├── reports.py      # Read-only display queries and financial rules
│   │       └── importers/
│   │           ├── __init__.py
│   │           └── revolut.py # Parse a known Revolut CSV format, no DB writes
│   └── tests/
│       ├── test_revolut.py
│       ├── test_imports.py
│       └── test_reports.py
│
└── frontend/
    ├── package.json
    ├── index.html
    ├── tsconfig.json
    ├── vite.config.ts
    └── src/
        ├── main.tsx          # React startup
        ├── App.tsx           # Account, import, preview, and result views
        ├── api.ts            # Typed calls to FastAPI
        └── App.css
```

Notes:

- This is a **starting tree**, not a request to create every listed file before it is used.
- Add a root `compose.yaml`, Dockerfiles, and VS Code launch settings when preparing the working self-hosted release. Their later introduction does **not** change the approved deployment architecture.
- `models.py`, `imports.py`, `reports.py`, and `App.tsx` are intentionally allowed to start small. Split them when they become hard to navigate or have demonstrably distinct responsibilities.
- Real uploaded bank files stay outside Git; tests use synthetic/anonymized samples.

## 3. Preserve the three financial concepts without three folder trees

The approved architecture defines:

| Concept | Early representation | Later examples |
|---|---|---|
| **What exists** — entities | `Account` and required reference data in `models.py` | Institution, Security, Asset, Liability, Currency |
| **What happened** — events | `Transaction`, `ImportBatch`, `ImportRow` in `models.py` | Trade, user-approved ReconciliationAdjustment |
| **What changed over time** — observations | `AccountBalance` with date, amount, currency, and source | PositionSnapshot, AssetValue, LiabilityBalance, FxRate, SecurityPrice, PriceIndex |

**These are domain concepts, not a requirement for one directory per concept.** As the application grows, move related models into `db/models/entities/`, `events/`, and `observations/` if doing so makes the code clearer. Keep table names, constraints, migrations, and external API behavior stable through such a refactor.

## 4. Minimal responsibilities (do not mix these)

| File | Does | Does not |
|---|---|---|
| `main.py` | Endpoints, request validation, response formatting | Financial calculations or CSV parsing |
| `db.py` | Engine/session lifecycle and SQLite configuration | Import rules |
| `models.py` | SQLAlchemy persistence models and constraints | HTTP handling |
| `importers/revolut.py` | File-specific parsing into normalized records and warnings | SQL queries or DB writes |
| `imports.py` | Import preview, duplicate decisions, persistence, atomic commit | Provider-specific parsing rules |
| `reports.py` | Account/transaction display values, as-of selections, quality indications | File upload handling |
| `api.ts` | Request/response integration | Authoritative financial calculations |
| `App.tsx` | Two user activities: import and view | SQLite access |

Use accurate money types (`Decimal` or validated integer minor units); **no floating-point financial calculations**. Keep parser outputs separate from ORM models so additional institutions do not depend on database internals. Never use an imported total/NAV and its component holdings as separate additive assets.

## 5. First user journey: one end-to-end feature

```text
Select or create account
          ↓
Upload a supported Revolut CSV
          ↓
Parse rows, balances, dates and currencies
          ↓
Preview new / exact duplicate / possible duplicate / invalid
          ↓
User resolves ambiguous items and confirms
          ↓
Atomic SQLite commit with source provenance
          ↓
View transactions + dated account balance + data-quality note
```

Minimum user-facing screens can be sections in **one `App.tsx`**:

- **Account selector / create account.**
- **Import.** Upload file, show detected account/currency/period and row counts, review warnings and possible duplicates, confirm or cancel.
- **Overview.** Show account balance *as of a date* only if supported by imported evidence or explicit user confirmation. Show transaction list and import status.

For the first slice, a single supported bank account may produce **an account value**, not a complete net-worth figure. Mark totals as *tracked/partial* when other accounts, positions, debts, or valuations are missing.

## 6. Minimum storage and non-negotiable guarantees

Create only the schema needed for the first slice, through **Alembic migrations**:

- `Account` — identity and currency/account context.
- `ImportBatch` — source file hash, parser version, account, period, timestamps/status.
- `ImportRow` — source row identity, normalized fingerprint, decision, and provenance linking to a canonical record.
- `Transaction` — normalized signed account movement, date, exact amount/currency, stable canonical identity.
- `AccountBalance` — dated cash balance observation, amount/currency, source and confirmation status.

Add small supporting constraints/association tables when required for *correct* import provenance, rather than forcing fragile polymorphic links. Do not add securities/trades/assets/liabilities tables until the corresponding working feature uses them.

**Must be true from the first import:**

1. Repeat-importing the same file cannot create duplicate financial movements.
2. Overlapping statements are matched **per record**, not rejected because their date ranges overlap.
3. Trusted provider IDs may support exact matching; matching only date/amount/description is **ambiguous** and needs review. Two legitimate identical payments must remain possible.
4. Multiple source rows can refer to **one canonical transaction**, with provenance retained.
5. The user sees a preview before a final commit; commit is atomic and idempotent.
6. If a real closing balance is unavailable, Matapan must not invent one by assuming all historical movements are present.
7. A saved balance has an **as-of date**, source and status; unknown is not zero.
8. No statement upload silently edits previously confirmed records.
9. Imported data remains separate from user edits and future synthetic reconciliation adjustments.

These guarantees are part of the approved architecture and are **not postponed for simplicity**.

## 7. Grow by adding working features, not folders

| Increment | User outcome | What to add to code |
|---|---|---|
| **Slice 0** | Open Matapan in VS Code and display a simple page from a running API | FastAPI, Vite/React, SQLite setup, one test, README |
| **Slice 1** | Import a real Revolut CSV and visualize results safely | Parser, preview/commit, canonical imports and duplicate decisions, balance observation, simple UI |
| **Slice 2** | Resolve missing transactions and confirm dated balances | Reconciliation logic, explicitly approved synthetic adjustments, revision/reversal, user-facing warnings |
| **Slice 3** | See combined cash + brokerage value | Interactive Brokers parser, security/position observation models, cash-vs-NAV guardrails |
| **Slice 4** | See meaningful multi-currency net worth | FX, assets, liabilities, dated valuations, quality/freshness, net-worth breakdown |
| **Further slices** | Broader self-hosted personal-finance product | Remaining parsers (SEB, Intesa, China Construction Bank, Alipay, WeChat), advanced reports, prices, inflation, optional AI |

**All MVP requirements from the v0.6 architecture remain mandatory before declaring the MVP finished**, regardless of slice numbering. In particular, reconciliation adjustments and cross-file overlap handling are MVP requirements, not optional future product ideas.

As soon as any file contains several unrelated responsibilities, extract the smallest sensible module. Examples:

- `models.py` → `db/models/...`
- `imports.py` → `services/import_service.py`, `services/duplicate_service.py`, `services/reconciliation_service.py`
- `reports.py` → `domain/valuation.py`, `services/net_worth_service.py`, `fx/service.py`
- `App.tsx` → feature folders for imports, reconciliation and net worth

Do not refactor merely to make the folder tree resemble a mature enterprise system.

## 8. What Codex should do first

**Task 1 — Runnable skeleton (Slice 0):**

> Read `docs/architecture.md`, `docs/code-structure.md` and `AGENTS.md`. Treat the architecture as fixed. Create the smallest runnable monorepo: Python/FastAPI backend, React/TypeScript/Vite frontend, SQLite + SQLAlchemy + initial Alembic migration, a health endpoint, one simple page that calls the API, and basic tests. Use `backend/src/matapan/` and `frontend/src/`. Add `.gitignore`, `.env.example`, README setup commands and a minimal root `AGENTS.md`. Do not scaffold future parsers, valuation models, AI, or large service directories. Run the available checks and report results. Do not commit private financial statements.

**Task 2 — Real importer and visualization (Slice 1):**

> Implement exactly one documented Revolut CSV variant from the supplied sample formats. The user must select/create an account, preview the import with safe row-level duplicate classification, explicitly confirm the import, then see imported transactions and the latest trustworthy dated balance. Preserve source provenance and safe overlapping-file behavior. Make the import idempotent and atomic, with synthetic test fixtures for exact reimport, overlapping statements, ambiguous identical purchases, missing dates and absent closing balances. Do not fabricate net worth or classify reconciliation adjustments as genuine income. Do not implement the remaining institution parsers yet.

**Rules:** Finish and verify Task 1 before Task 2. Never use schema-reset shortcuts on user data. Keep source evidence and migration history. Once a slice works, refactor only where needed to support the next slice.

## 9. What has not changed

This document **only simplifies code organization and the order in which files are created**. It does not supersede or amend the approved `MATAPAN_ARCHITECTURE_V06_IMPORT_OVERLAPS_RECONCILIATION.md` requirements covering:

- The net-worth-first product goal and multi-institution roadmap.
- React + TypeScript, FastAPI/Python, SQLite, SQLAlchemy, Alembic, Docker-based self-hosting.
- Entities / events / observations and multi-currency financial data.
- Bank and broker import support in the MVP, transaction provenance and overlap deduplication.
- Dated balances, manual valuation, reconciliation and user-approved synthetic adjustments.
- Data-quality/reliability indicators, safe reporting and correct asset aggregation.
- Privacy, authentication, audit, tests, backups and recoverability.

**One-sentence direction:** Start with *import a real statement → review it → save it safely → visualize a trustworthy dated account value*. Expand toward the frozen Matapan architecture one completed feature at a time.

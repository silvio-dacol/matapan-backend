# Matapan account workspace

The React/TypeScript frontend connects to the existing FastAPI backend. It uses a
warm light palette with dark green actions and adapts to desktop and mobile.

For a step-by-step walkthrough, see
[the easy frontend guide](../docs/easy_frontend_use.md).

Start the backend and apply its migrations as described in
[backend/README.md](../backend/README.md). With Node.js 20.19+ or 22.12+ installed,
run from this directory:

```powershell
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173. Keep the backend on http://127.0.0.1:8000. Vite proxies
API requests so previews, refreshes, confirmation, and cancellation share the
HTTP-only session cookie. CORS changes are unnecessary. `MATAPAN_API_TARGET` can
select a different local backend address before starting Vite.

## First account journey

1. Create an account with its currency. For Revolut, select Current or Savings;
   each product/currency pair needs a separate account.
2. Select **Import statement**, choose a supported English Revolut CSV, and
   preview it. Review observed transaction dates, counts, source balance evidence,
   and warnings. The preview does not accept movements or balances.
3. Compare existing candidates for possible duplicates. Choose **Keep as a
   separate movement**, **Link to existing match**, or **Skip this row**. Invalid
   rows require an explicit skip; rows from other products/currencies are excluded.
4. Approve the decisions and selected balance evidence, then **Confirm import**.
   The account report and activity refresh. Reimporting the same file cannot add
   its movements again.
5. If history is incomplete or a balance is missing, select **Confirm balance**.
   Enter the actual amount, date, optional note, and explicit confirmation.
   Monetary input uses decimal text, never floating-point conversions.

The report date selects dated evidence through the backend. The activity list
shows all imported dates with pagination. Balance evidence retains historical
observations and confirmations, including observations after the report date.
Both account selection and adding an account are disabled during a form or import
review to avoid changing the destination account midway through the work.

## What the figures mean

- **Confirmed by you** identifies a dated manual confirmation.
- **Source reported** identifies a Revolut running balance at its original local
  timestamp; it is not presented as a verified end-of-day balance.
- **Conflicting evidence** leaves the amount unavailable and preserves all
  observations. Selecting a winning observation is not yet supported by the API.
- An earlier observation is explicitly carried forward, rather than described
  as confirmed for a later date. Missing evidence is unavailable, never zero.
- History coverage remains unverified even after a balance confirmation. The UI
  does not compute balances from an arbitrary subset of movements.

This slice covers account cash and a partial financial picture. Reconciliation,
synthetic adjustments and their revision, brokerage, FX, consolidated net worth,
authentication, and self-hosted production packaging remain subsequent work.
The development and preview servers bind to loopback.

## Verification

```powershell
npm.cmd run build
npm.cmd test
```

The build includes strict TypeScript checks. Playwright starts Vite on port 5174
and a real API on port 8001, using a newly migrated disposable database under the
ignored `.test-data/` directory. It refuses to reuse running servers on these ports
and never points at the user's financial database. Tests use the backend's
synthetic CSV fixtures. No original bank exports are needed.

Install the backend's development dependencies first. Browser tests default to
`backend/.venv/Scripts/python.exe` on Windows and `backend/.venv/bin/python`
elsewhere. Set `MATAPAN_TEST_PYTHON` to use another Python environment with Matapan
installed. Windows tests use installed Microsoft Edge in headless mode. On other
platforms, install Playwright's Chromium with `npx playwright install chromium`.

Desktop/mobile tests cover preview versus commit, exact reimport, reviewed
overlaps and source provenance, invalid-row decisions, cancellation, exact large
amounts, dated confirmation, past reports, conflicting balances, persistence after
reload, preview expiry, concurrent-import recovery, and connection recovery.
Screenshots and failure traces stay in ignored
`test-results/`. Do not use private financial data for those artifacts.

`npm.cmd run preview` serves the built frontend locally with the same API proxy.
Production hosting needs a same-origin API reverse proxy; the generated static
assets alone do not include or replace the backend.

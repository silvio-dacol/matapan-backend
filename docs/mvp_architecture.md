# Matapan — Architecture and Codex Blueprint

**Version:** 0.6 — net-worth-first MVP, import overlap prevention, user-approved reconciliation adjustments  
**Status:** Proposed product and engineering decisions for review (updated with statement evidence, duplicate management and reconciliation adjustments)  
**Primary user promise:** Import bank and brokerage data from different countries and currencies, then see a trustworthy, explainable consolidated financial position.  
**Deployment:** Local-first, initially single-user, home server or local machine.

## 0. What changed through v0.6

**v0.6:** Explicitly add MVP transaction-event ingestion for bank formats that contain transaction rows; cross-file duplicate detection and review of ambiguous matches; dated account/currency reconciliation with user-approved synthetic adjustments and future adjustment revision when late-arriving transactions are imported. See Section 14. **A confirmed closing balance is never added on top of a synthetic adjustment when calculating net worth.**

**v0.5:** The MVP includes dated balance confirmation, source-versus-transaction reconciliation, reliability statuses, material data-quality warnings, and a carefully defined optional numeric net-worth quality index. See Section 13 for authoritative reliability and implementation rules. This section refines the v0.4 import workflow without changing the import-first commitment.

### Previous decision: imports in the MVP

**Import is an MVP requirement, not a future milestone.** The first useful session must work as follows:

1. Create/select a bank or brokerage account.
2. Upload a *supported real institution export*, not merely an internal Matapan CSV template.
3. Review a preview of detected balances, positions, and any transactions that the file supports; see warnings, overlapping statement periods, and suspected duplicates.
4. Confirm import and see the consolidated net-worth report change immediately; optionally reconcile a dated balance discrepancy with a clearly marked, user-approved adjustment.
5. Inspect each figure's currency, date, and origin; manually fill the gaps (e.g., house or mortgage).

Speed constraint: **support a small number of real statement formats impeccably**, rather than many formats heuristically. The first bank and broker formats must be selected from real representative samples; Revolut and Interactive Brokers are *candidates*, not asserted formats already implemented or guaranteed to expose every field needed.

## 1. User outcomes and scope

The MVP must answer:

- What is the total value of my tracked cash, investments, other assets, and liabilities in my reporting currency?
- How is it distributed across institutions and currencies?
- How did it change between dates *with sufficient source coverage*?
- Which values are missing, stale, manually entered, or unreconciled?
- Can I reimport a statement without duplicating data or overwriting user corrections?

### Required MVP experience

- Initial setup: reporting currency, account creation, private access.
- Import center: upload, account/format selection or detection, preview, problems, confirmation, import history.
- Support at least **one actual bank export and one actual brokerage positions/holdings export** end to end. If a broker export includes cash, ingest it separately from securities; if it includes a total equity/NAV value, use it only for reconciliation.
- Manual entry/editing for balances, position valuations, assets, and liabilities when exports are unavailable.
- Net-worth dashboard: assets, liabilities, total tracked net worth; breakdown by component, account/institution/currency; reporting date, provenance, warnings, **reliability status and actionable issues**, and drill-down.
- Dated observations, meaningful historical comparison, and **dated user balance confirmation where necessary**.
- Deterministic daily FX conversion with explicit source/date; support missing-rate warnings.
- Idempotent imports, overlap-aware record deduplication, user-reviewed possible duplicates, dated reconciliation adjustments and backup/restore for self-hosting.
- Distinguish missing transaction coverage from missing or stale balance/position evidence; do not penalize net-worth reporting for transaction gaps when reliable dated balance snapshots exist.

### Not required for MVP

- Automatic import from every institution; account aggregation via bank APIs; OCR or PDF parsing; Ollama or cloud AI; comprehensive transaction categorization and budgets; trade-derived positions; performance attribution; tax lots; inflation-adjusted wealth; multi-tenant hosting.
- **Exception / v0.6 MVP requirement:** For a supported bank format containing movements, parse and retain a *minimal immutable transaction event* needed for overlap detection and optional balance reconciliation. Detailed category management, cash-flow dashboards and investment-performance processing remain later scope. Transaction ingestion is not a substitute for a verified cash balance.

## 2. Architecture: optimize for incremental delivery

```text
React + TypeScript (Import, Accounts, Dashboard, Data Quality)
                   |
             Versioned REST API
                   |
             Python / FastAPI
                   |
        Application use-case services
          /        |         \
      Import    Valuation    FX / Quality
        |          |            |
  Parser adapters |            |
        \          |           /
            SQLAlchemy / SQLite

  Optional later: market-price provider, AI, additional parsers
```

**Project organization:** single Git repository, with separately structured `/backend` and `/frontend`. Keep a modular monolith; do not add microservices, Redis/Celery, or PostgreSQL for the single-user MVP without measured need. SQLite files live in persistent local storage, never Git. Run locally and via Docker Compose. API endpoints own writes; parsers never mutate SQLite directly.

Recommended layout:

```text
matapan/
  backend/
    src/matapan/
      api/
      domain/
      services/
      importers/
        contracts.py
        registry.py
        institutions/
      db/
      fx/
    migrations/
    tests/
      fixtures/synthetic_statements/
  frontend/
    src/features/
      imports/
      net-worth/
      accounts/
      data-quality/
  docs/
  compose.yaml
  AGENTS.md
  README.md
```

Before deciding whether to rewrite existing Rust parsers, inspect the actual repository and reuse validated functionality when cheaper and safer; uploaded legacy design notes describe a Rust app, while Python/FastAPI is the current proposed implementation direction.

## 3. The domain model: entities, events, observations

Retain the user's existing organizing principle:

- **Entities / what exists:** `Currency`, `Institution`, `Account`, `Security`, `Asset`, `Liability`, `UserSettings`.
- **Events / what happened:** `ImportBatch`, `ImportRow`, minimal `Transaction` records from supported bank statements, user-approved `ReconciliationAdjustment` events; full transaction analytics and `Trade` processing later.
- **Observations / what changed over time:** `AccountBalance`, `PositionSnapshot`, `AssetValue`, `LiabilityBalance`, `FxRate`; later `SecurityPrice`, `PriceIndex`.

Implement only the tables required for MVP flows, retaining these names where practical. Proposed corrections to the provided ERD:

1. **Import lineage:** replace or extend `Import` with `ImportBatch` and `ImportRow` (or equivalent). An accepted observation links to its source import row; manual observations record manual provenance.
2. **Cash semantics:** `AccountBalance` means cash balance only, never total brokerage equity. A brokerage account can hold balances in multiple currencies; add `currency_code` to the observation, together with date and provenance.
3. **Positions:** use an internal `Security.id`; `isin` is nullable and uniquely indexed when present. `PositionSnapshot` includes account, security, date, quantity, provider-market-value, valuation currency, and provenance.
4. **Asset and liability snapshots:** retain `AssetValue` and `LiabilityBalance` with dated values, currency, source, and inclusion scope. Do not substitute purchase price for current value or initial loan amount for outstanding debt.
5. **FX:** explicit base/quote direction, observation date, provider/source, and exact decimal handling. EUR may be a pivot but is neither guaranteed available nor forced as the display currency.
6. **Conflicts:** define an explicit selected/accepted observation when two sources report the same economic item/date, keeping both source records for traceability. Never select by arbitrary insertion order.
7. **Idempotence and overlapping statements:** import-level file hash plus account/parser context, provider identifiers where trustworthy, and row-level normalized identity; two genuine identical transactions are not necessarily duplicates. Distinguish `duplicate`, `possible_duplicate`, `new`, `conflict` and `invalid` in preview. See Section 14 for match and review rules.
8. **Historical inclusion:** archived accounts still appear in reports for dates when they were in scope. Missing observations are not zero.
9. **Reconciliation adjustments:** create auditable, reversible, account/currency/period-scoped synthetic events only after explicit user approval. Never present them as imported real transactions or include them in income/expense. See Section 14.

**Numeric policy:** No binary floating point for authoritative money/quantity/rate calculations. Use signed integer minor units for ordinary fiat money where appropriate and `Decimal` with explicit validated storage for high-precision quantities, FX, and pricing; document rounding and SQLite exactness constraints. Support multicurrency brokerage cash without asserting every account is single-currency.

### Import entities (suggested essential fields)

`ImportBatch`: `id`, `account_id`, `institution`, `detected_format`, `parser_version`, `original_filename_safe`, `file_sha256`, `received_at`, `status`, `record_counts`, `warning_summary`.

`ImportRow`: `id`, `batch_id`, `row_number`, `record_type`, `provider_record_id?`, `normalized_fingerprint`, `status`, `validation_errors`, `created_record_id?`, `created_record_type?`, `matching_existing_record_id?`, `review_decision?`; source raw payload retention is optional and privacy-controlled.

Imported **observation**: normalized account/security/asset identity, `as_of_date`, numerical value, currency, source row reference, observation status, timestamps. Avoid polymorphic foreign keys if database integrity becomes fragile: explicit link tables/columns are acceptable and preferable to clever generalized frameworks.

## 4. Import system and parser contracts

The import pipeline is:

```text
Upload file
  -> Validate size/type (do not trust extension alone)
  -> Detect candidate parser or allow explicit selection
  -> Parse without persistence side effects
  -> Normalize to typed records
  -> Validate currency, quantity, dates, account mapping
  -> Resolve record identities, file overlaps and duplicate/conflict candidates
  -> Preview new/duplicate/ambiguous records, components and reconciliation differences
  -> User approves/remaps/rejects rows as appropriate
  -> Atomic database commit
  -> Recompute net-worth report and show import result
```

A parser returns structured observations/events and warnings; it **never returns a precomputed net worth as the authoritative truth** and never writes to the database.

Suggested typed normalized records:

- `CashBalanceObservation(account, currency, as_of, balance, source_reference)`
- `SecurityPositionObservation(account, security_identity, as_of, quantity, market_value, valuation_currency, source_reference)`
- `AccountTransactionEvent(...)` for supported movement exports (minimal immutable event for overlap detection/reconciliation, not a full spending-analysis module); not required to calculate net worth when reliable balance evidence exists.
- `PortfolioAggregateObservation(account, as_of, total_equity, currency, source_reference)` for **reconciliation only**, never additive to positions plus cash.
- `ImportIssue(severity, row, field, message)`.

Do **not** infer an authoritative bank balance by summing an arbitrary subset of transactions. Only ingest a cash balance if source supplies one, or if opening balance, transactions and coverage are sufficient and verified. If not, expose a request for a manual as-of balance and label the import as incomplete for net-worth valuation.

For a brokerage export that has positions but not provider-reported market values, either clearly calculate value from a validated price and quote date or mark the position unvalued. Do not silently invent current prices.

A parser is versioned. Store `parser_id` and `parser_version` with the batch; add fixture-driven regression tests for every supported format. File and row fingerprints must be stable across repeated imports. Provider-record IDs should take precedence when reliable; ambiguous matches need user confirmation. For cross-file overlap handling and matched provenance, use the source-scoped identity and review policy in Section 14.

**File support plan:** real institution CSV/XLSX exports first, depending on verified actual samples. Avoid a universal parser and do not promise PDF/OCR in the MVP. Prefer built-in `csv` for CSV; use `openpyxl` or equivalent only when actual supported exports require Excel.

## 5. Financial reporting invariants

At reporting date D, report:

`Tracked net worth = bank cash + brokerage cash + individual security market values + other asset values - liability balances`, converted to the selected reporting currency.

- Never add a brokerage account's aggregate NAV to the cash and security positions already composing it.
- Market values come from explicit source snapshots or documented valuation calculations, not trade costs.
- Each selected observation must be dated on/before D; show observation age and provenance.
- Use observed FX rates and an explicit missing/stale FX policy. Same-currency conversion is exactly 1.
- A missing required observation yields **partial/unavailable**, not a complete-looking zero-filled figure.
- `Net worth change` is not automatically `investment return`; deposits, withdrawals, capital flows, market prices and FX changes may all contribute.
- Carry-forward values must be visibly labeled, particularly for property valuations.
- Show user what is included in `tracked` net worth; do not imply unknown holdings or debts are known.

Report API should return component breakdown and `status: complete|partial|unavailable`, missing/stale/conflicted items, source dates, and FX rate dates. Never lose provenance when the user corrects an imported figure; preserve the original source and a separate effective/accepted correction where feasible.

## 6. Minimal API surface

```text
GET/PATCH /api/v1/settings
GET/POST  /api/v1/accounts
GET/POST  /api/v1/securities
GET/POST  /api/v1/assets
GET/POST  /api/v1/liabilities

POST      /api/v1/imports/preview
POST      /api/v1/imports/{preview_id}/commit
GET       /api/v1/imports
GET       /api/v1/imports/{id}
POST      /api/v1/imports/{preview_id}/duplicate-decisions
GET       /api/v1/accounts/{id}/reconciliations
POST      /api/v1/accounts/{id}/reconciliations/preview
POST      /api/v1/reconciliations/{id}/accept-adjustment
POST      /api/v1/reconciliations/{id}/reverse-adjustment

POST      /api/v1/accounts/{id}/cash-balances
POST      /api/v1/accounts/{id}/positions
POST      /api/v1/assets/{id}/valuations
POST      /api/v1/liabilities/{id}/balances

GET       /api/v1/reports/net-worth?as_of=YYYY-MM-DD&currency=CHF
GET       /api/v1/reports/net-worth/history?from=...&to=...
GET       /api/v1/reports/data-quality
```

Implement endpoints only when demanded by the current vertical slice. Preview state must expire, be bound to the user's session, and be private; commit must not accept arbitrary unvalidated client-provided records.

## 7. Roadmap optimized for speed and credible import value

### M0: Runnable skeleton + accounting proof (foundation)

- Repo setup, API, frontend shell, database migrations, test harness, Docker Compose.
- Seed **synthetic** cash, positions, other assets, liabilities, and daily FX; implement one basic, tested net-worth calculation (even if the UI is initially minimal).
- Private deployment defaults and basic access protection appropriate to the environment.

**Exit:** deterministic net-worth unit test and running frontend/API.

### M1: Real import-to-net-worth vertical slice (first demo)

- Select **one actual institution export** from provided samples; implement its parser, preview, user confirmation, import lineage, overlapping-statement duplicate checks, and one matching cash-or-positions observation pipeline. For a bank movement file, persist minimal transaction events and verify reconciliation against source-reported balances.
- Show affected account and an explainable net-worth dashboard.
- Support manual completion of missing inputs and currency-rate data where necessary.

**Exit:** upload a real supported export; see the correct updated position immediately; reupload or partially overlapping import creates no confirmed duplicates; possible duplicates are reviewed; any gap/reconciliation adjustment is explicit and auditable.

### M2: Complete the sellable cross-institution MVP

- Add a second real format of the **other type**: if M1 was bank cash, M2 is brokerage holdings/cash; if M1 was broker, M2 is bank cash. Finish the bank transaction overlap, reconciliation decision and user-approved adjustment vertical slice no later than M2.
- Add manual assets/liabilities, multi-currency breakdown and verified daily FX sourcing policy, history by meaningful dates, reconciliation diagnostics, import-history screen, and restoration tests.
- Secure home-server deployment, tested backup/restore and user-readable setup.

**Exit:** import a supported bank statement **and** brokerage holdings export, including overlapping bank statements; accept or leave unresolved a reconciliation difference; add a property and loan manually; display reproducible multi-currency net worth as of a chosen date with clear data-quality warnings.

### M3: After MVP — more supported institutions and operational convenience

- Add real institution formats using fixtures, improved mapping/field error handling, optional FX scheduling and automated recurring imports when supported. Keep source-specific parser contracts.

### M4: After MVP — activity and analytics

- Extend already stored canonical bank `Transaction` records with `Category`, transfer pairing and cash-flow analytics; `Trade` and investment performance; position reconciliation; inflation `PriceIndex`; optional local Ollama suggestions.

**No artificial requirement to implement M3 or M4 before the product can be used for net-worth aggregation.**

## 8. MVP acceptance tests (must be automated where applicable)

**Read in conjunction with the additional reliability-specific acceptance tests in Section 13.9.**

1. Repeat upload of same export for same account/parser produces no duplicate financial observations. For overlapping-file and reconciliation examples see additional tests in Section 14.9.
2. Different file names but equivalent source records are detected as duplicates when stable source identity is available, even if their statement date ranges differ.
3. Two legitimately equal-valued items are not silently collapsed into one; provider-neutral matching without reliable identity becomes a user-review candidate.
4. Validation failures or interrupted commits do not leave partial accepted imports.
5. Cash balance and portfolio aggregate equity are not counted twice.
6. Broker USD cash and EUR-denominated position market value convert independently to CHF.
7. Missing FX, balance or market value creates a visible incomplete report, not a fabricated complete number.
8. Future observations are not used in past-date reports.
9. Imported original and later user-approved correction remain traceable.
10. Original currency amounts remain unchanged by reporting-currency switches.
11. Archived historical records still contribute to correct historical reports.
12. A restored database yields the same computed report given identical data and configuration.
13. Sensitive statement content is absent from app logs.
14. Unknown or unsupported files fail clearly without guessing a compatible parser.
15. Reconciliation totals (broker equity) are compared to cash-plus-positions but never added to net worth.

## 9. Security and operations

Financial files are private. Default to loopback/LAN-only access; do not publish unauthenticated APIs or allow unrestricted CORS. Use authentication appropriate to the actual network exposure. Validate uploads (including size), redact logs, limit sensitive file retention, and keep backend/data separate from Git. Back up SQLite consistently using SQLite's online backup API or an equivalent consistent snapshot, not an uncoordinated file copy. Verify restore. If remote access is required, prefer private VPN or authenticated HTTPS ingress; not a default public exposure.

Do not persist uploads permanently unless needed for an explicit replay/audit feature. A hashed source file and sanitized row provenance may be sufficient for MVP; disclose retention choices in the UI.

## 10. Instructions for Codex

1. Inspect the repository, uploaded design documents and actual sample statement formats before changing code. Preserve proven existing parsers where sensible; do not assume all parsers must be rewritten in Python.
2. **Treat import as an MVP requirement.** Do not move it into a later phase merely to deliver a manual-only dashboard.
3. Implement only the requested milestone, smallest vertical slice first; start with M0 unless the user explicitly selects another.
4. Identify exact first parser fixture and expected normalized output *before coding*; if no real samples are available, request them rather than inventing institution column mappings.
5. Document entity relationships, numeric policy, import preview/commit semantics, and required migrations.
6. Test finance invariants and idempotent import behavior; report real test/lint results.
7. Never silently fabricate balances, security valuations, FX rates or transaction coverage.
8. Never destructively reset a user's finance database to simplify migrations or local debugging.
9. Keep explanations, provenance, and incompleteness visible to the end user.
10. Stop at the milestone boundary and summarize shipped behavior, remaining limitations, and next acceptance criterion.

## 11. Decisions still needed before M1

- **Which two real exports?** Select one bank and one brokerage format from representative sanitized CSV/XLSX samples. Revolut and Interactive Brokers are good candidates *if their actual exports contain the necessary balance/position observations*.
- **What do the files actually contain?** A bank transaction export with no verified balance cannot by itself power a correct net-worth number. Source coverage determines whether balance ingestion is automated or needs manual completion.
- **What is meant by a complete imported date?** Define import cut-off and record coverage separately for account cash and portfolio positions.
- **How will valuation conflicts be reviewed?** Define deterministic selected-observation precedence and user override semantics.
- **Which FX data source and staleness policy?** Name and test the source rather than assuming daily rates are universally available.

## 12. Product definition of done

The first sellable MVP lets a self-hosting user **import a supported bank export and a supported broker positions export**, resolve overlaps/duplicate warnings and user-approved balance adjustments, manually add missing real assets or liabilities, and obtain an auditable multi-currency net-worth dashboard with historical as-of views, backup/restore, and explicit data completeness. A manual-only net-worth calculator does **not** satisfy the MVP.

---

**Source continuity:** This blueprint builds upon `database_erd.dbml`, `matapan.md`, `how_to_look_at_data.md`, and `architecture_to_aim_for.md`, plus v0.2/v0.3 discussions. Changes to imported source design are recommendations rather than claims that the original ERD already implements them.

## 13. Net-worth reliability and reconciliation (v0.5, MVP requirement)

### 13.1 Product requirement

Matapan must distinguish **the amount it can calculate** from **how well the underlying evidence supports that amount**. Display the tracked net-worth amount, as-of date, report completeness status, a human-readable reliability rating, and the most material issues to resolve. A score must never conceal an unavailable balance, stale valuation, or double counting.

Use the user-facing name **Net-worth reliability**, **not confidence percentage**. A rating of `70/100` is a deterministic data-quality index, **not a 70% statistical probability that the net-worth number is correct**. Do not call it accuracy, probability, precision or a confidence interval. Financial completeness of assets not disclosed by the user cannot be inferred from imported exports.

This feature is part of the MVP because it differentiates Matapan from an ordinary spreadsheet, helps people trust financial reports, and gives explicit actions to improve them. Build a transparent rule-based version, not an AI-based confidence model.

### 13.2 Two distinct concepts, never conflated

**Scope/completeness** answers: *Are the accounts, holdings, debts and reporting dates covered?* Example states: `unreviewed`, `partial`, `user-reviewed`; plus `complete/partial/unavailable` for calculation status. User review is not proof of complete real-world financial coverage.

**Reliability** answers: *For the tracked amounts, how good and current is the source evidence?* Show a 0–100 **quality index** only when enough valuation evidence exists to calculate it meaningfully, and explain its input factors. If significant amounts are missing or conflicted, show `Not available / needs attention` rather than a deceptively precise score.

Track **transaction coverage separately**. If a bank provides a trustworthy dated closing balance, missing transactions from earlier in the statement do **not automatically** invalidate that balance for an as-of net-worth report. They do reduce confidence in transaction-derived balance changes, cash-flow reports and the ability to reconcile from an earlier checkpoint. Missing records **do** affect net-worth reliability when the cash balance is *inferred* from incomplete movement history.

### 13.3 Evidence dimensions per component

Evaluate each net-worth component individually (including liabilities):

| Dimension | Question | Typical warning |
| --- | --- | --- |
| Coverage | Is the economic item represented and in scope for the date? | Account declared but no usable cash observation |
| Freshness | How old is the latest usable observation **relative to the report date**? | Property last valued years before report date |
| Provenance | Where did this value come from? | Undocumented manual estimate |
| Reconciliation | Does it agree with independent source totals or a dated user-confirmed balance? | Cash plus positions differs from broker NAV |
| Valuation basis | Is it a statement balance, market mark, appraisal or guess? | Purchase price presented as current property value |
| FX quality | Is a usable source rate available for the relevant date? | Missing or overly stale conversion rate |
| Conflicts | Are two observations for same item/date contradictory? | Statement balance and manually reported balance disagree |

For each issue store or derive: severity (`blocker`, `warning`, `information`), target, as-of date, source reference, description and one recommended action. Materiality should affect prioritization. An unresolved conflict or missing FX must not be silently normalized into a numeric value.

### 13.4 User confirmation and dated reconciliations

At an appropriate point in the import flow ask, for example: “For the account ending ••••, the statement reports a balance as of 30 Nov. Is that balance correct for **that date**?” A confirmation of a historical balance must not be treated as a confirmation of today's balance. If users enter a *current* balance, record its own as-of timestamp and source; retain rather than overwrite the imported historical observation.

Suggested states for each account/currency/as-of date:

- `source_reported`: amount explicitly present in an imported statement
- `user_confirmed`: user attests to a dated amount or confirms a source-reported snapshot
- `reconciled`: an independently computed expected balance agrees with the dated snapshot within a documented tolerance
- `estimated`: amount derived under stated assumptions but not verified
- `conflicted`: two candidate readings disagree and require explicit selection
- `missing`: no usable evidence at the target date

Reconciliation calculation for a period with complete movement coverage:

`expected_closing_balance = confirmed_opening_balance + sum(signed movements during the covered interval)`

`difference = reported_closing_balance - expected_closing_balance`

The service must check movement boundaries, account/currency, booking-versus-value dates, pending versus booked movements, fees and whether an export includes all products/pockets. If coverage is incomplete, do **not** label the result reconciled just because the difference happens to be zero. FX-converted totals are never substituted for native-currency reconciliation.

Never replace an imported source value when a user corrects it. Save the original and a dated user confirmation/correction with provenance. Re-run reconciliation after new imports or balance updates.

### 13.5 Recommended scoring model (transparent and versioned)

MVP can first implement deterministic `excellent / good / review / insufficient evidence` ratings and reasons. Add a numeric 0–100 quality index once the rules are tested. Do not delay the importer or net-worth calculation for complex score calibration.

When a numeric score is displayed, use a documented versioned policy:

- Compute a component evidence quality score `q_i` in `[0,100]` using explicit rules for age, source, reconciliation, valuation basis and FX. A `blocker` can make the component unscorable. A user can supply/confirm evidence but cannot directly set `q_i`.
- Compute exposure weight from the **absolute reporting-currency contribution** `w_i = abs(v_i)`, treating liabilities as material too. Do not weight a mortgage as negative reliability.
- As a provisional aggregation only: `quality_index = round(sum(w_i * q_i) / sum(w_i))`. Recompute from source evidence on every report; include `policy_version` in the API. Document the limitations: a high-quality large account can overshadow poor-quality small accounts. Also show blocker counts and worst/relevant issues independently.
- If no material tracked value exists, source coverage is unknown, a major component cannot be valued, or a critical double-counting conflict persists, hide the number and return `insufficient_evidence` / `partial`, with actionable issues.
- Store policy thresholds in one backend configuration module. Make them asset-class-aware and tested; **do not** embed magic confidence percentages in parsers or the frontend.

Do not pretend to have a calibrated statistical uncertainty interval. Optional *future* valuation ranges, especially for illiquid assets, must be based on explicit low/high valuation assumptions and must remain distinct from the quality index.

### 13.6 User-facing report concept (illustrative only)

```text
Tracked net worth                           CHF 300,000
As of                                       2026-09-30
Completeness                               Partial (review needed)
Net-worth reliability                      70/100 (illustrative only)

Cash                     CHF  20,000       Verified current snapshot
Investments              CHF  80,000       Broker snapshot, checked
Home                     CHF 500,000       Estimated, last reviewed 2022
Mortgage                -CHF 300,000       Last confirmed 6 months ago

Actions:
1. Refresh the property's valuation.
2. Confirm the remaining mortgage balance.
3. Resolve a statement coverage warning on one linked account.
```

Even if the UI displays a sample numeric score, it must explain it does **not** express a probability and is derived only from tracked/known items. Avoid badges such as “Complete” unless the reviewed scope and date requirements have truly been met.

### 13.7 Additional or refined database concepts

Keep the existing dated observation tables; avoid building an all-purpose flexible key-value schema.

**On each observation** (cash, position, asset, liability): include its actual `as_of_date`, source type, origin row or manual provenance, recorded timestamp, optional valuation method, and accepted/superseded state. A future reporting date must never select a newer snapshot. A user-entered current amount creates a new observation, not a rewrite of an old statement.

**ImportBatch**: capture `period_start`, `period_end`, `generated_at` when supplied, parser id/version, and whether the export appears to include cash balance, positions and activity. Export generation time does not mean the exported data are current at that time.

**BalanceConfirmation** (or equivalent lightweight audit record): `id`, `account_id`, `currency_code`, `snapshot_as_of`, `confirmed_balance`, `confirmation_kind`, `confirmed_at`, `linked_observation_id?`, `note?`. If it merely confirms an existing snapshot, store an attestation rather than a duplicate balance observation.

**ReconciliationResult**: account/currency/period, opening/closing observation references, coverage status, expected/observed amounts, native-currency difference, status, evaluated timestamp, algorithm version, and issue codes. It may be calculated on demand for MVP; persist confirmation events, adjustments, duplicate decisions and selected observation choices even if computed results are ephemeral. See Section 14 for period boundaries and adjustment lifecycle.

**ReportQuality** is a computed output, not an authoritative net-worth database table. Derive it from evidence and policy; cache only as a reproducible versioned optimization later.

For extra property valuation fields include provenance such as `market_estimate`, `professional_appraisal`, `purchase_price`, `user_estimate`, `broker_statement`, with per-source dates. A stale home valuation does not imply the property is absent.

### 13.8 Source-specific findings from uploaded sample files (structure only)

These observations are based on **format/header inspection**, not full importer validation or a claim that every record is complete:

| Sample | Observable structure | Architectural implication |
| --- | --- | --- |
| Revolut CSV (2 exports) | `Type`, `Product`, `Started Date`, `Completed Date`, `Amount`, `Currency`, `State`, `Balance` | Running balance is available per row; map pockets/products and completed dates carefully before treating it as one account's closing balance. |
| SEB checking/savings XLSX | `Booking date`, `Value date`, `Amount`, `Balance` | Supports native-currency dated balance checkpoints and separate booking/value-date policies. |
| Interactive Brokers activity CSV | Sectioned report with `Cash Report`, `Open Positions`, `Net Asset Value`, `Trades` | Supports independent brokerage cash and security positions; aggregate NAV is a reconciliation control, **not** an additional asset. |
| Intesa Sanpaolo movements XLSX | Transaction-style fields (`Data`, `Operazione`, `Valuta`, `Importo`) | Transaction records need account reconciliation; a movements export alone is not proof of current balance. |
| Intesa Sanpaolo patrimonio XLSX | Holdings columns including `ISIN`, `Quantità`, `Prezzo Mercato`, `Data-Ora`, `Controvalore`; liquidity area | Promising direct holdings/valuation source; validate subtotal semantics and as-of timestamps before import. |
| WeChat XLSX (3 exports) | Activity details and export period; payment method and trade/order identifiers | Primarily payment activity. Bank-card-funded purchases may overlap bank transactions; do not treat all spending as reduction of an independently valued WeChat wallet balance. |
| Alipay CSV | Chinese-language multi-line preamble, dated export interval and transaction header; GB18030-readable | Payment activity and potential wallet events; imported records do not by themselves verify wallet/account balances; handle encoding and payment-source overlap. |
| China Construction Bank XLS | Legacy binary `.xls` workbook | Format identified, but detailed schema/parsing is **not yet validated** by the current XLSX inspection workflow. Treat as unverified until a dedicated fixture test exists. |

Production code must **never** include these uploaded users' private statement contents as test fixtures. Generate synthetic examples with the same layouts/semantics and scrub identifiers and amounts. Do not commit original bank files, spreadsheet contents, account numbers or transaction descriptions into Git, documentation, logs or CI artifacts.

### 13.9 New acceptance tests

1. A source-reported closing balance can receive a good net-worth quality assessment despite gaps in earlier transactions, while the transaction-history completeness warning remains visible.
2. A derived closing balance with a missing movement interval is *not* classified as reconciled or authoritative.
3. A snapshot on 2025-11-30 cannot be marked user-confirmed `today` solely because the user reviews it in 2026.
4. A home last valued years ago is still included with a clear age and valuation warning; it is not arbitrarily zeroed.
5. A mortgage with outdated outstanding balance lowers reliability and surfaces a request for a new dated debt balance.
6. Unavailable FX or a critical double-counting conflict forces partial/unavailable rather than an invented precise reliable number.
7. New bank/broker exports and user confirmations recalculate quality deterministically without overwriting source data.
8. A brokerage NAV is used only to reconcile brokerage cash plus positions; not added as another asset.
9. WeChat/Alipay card-funded purchases do not reduce a wallet balance *and* a bank account balance twice.
10. Score weights count liabilities by absolute exposure and report policy version; the same input evidence and version yields the same output.
11. The quality report highlights the top material issues with concrete next actions and their as-of dates.
12. User can correct a balance while preserving its original source and confirmation history.

### 13.10 Revised engineering execution order

**M0:** Implement source-backed net-worth calculations and typed observation/reliability *statuses*. Set up synthetic, dated cash/positions/assets/liabilities/FX tests. No numeric score algorithm necessary yet.

**M1:** Implement a real bank parser with preview, balance as-of recognition, overlap-aware duplicate prevention, minimal transaction-event persistence, and a prompt to confirm/check a dated balance. Calculate the net-worth result and show warnings.

**M2:** Add a broker parser for cash/positions/NAV; reconcile its reported NAV; finish explicit approval/reversal of dated synthetic bank reconciliation adjustments; add other-asset and liability snapshots, freshness rules, completeness review, and actionable data-quality explanations. Introduce a versioned numeric reliability index **only after** evidence rules and regression fixtures are stable.

**M3+:** Additional institution parsers, longitudinal transaction coverage and cash-flow reconciliation, user-driven reminders to refresh valuations, and optional advanced uncertainty/range modeling. AI must not be the authority for reliability scores.

### 13.11 Updated Codex instruction

The user-facing requirement is not “display a confidence number”. The requirement is “make financial trustworthiness understandable and actionable.” Before coding a scoring function, Codex must implement a typed evidence model with specific causes, observation dates and reliable/partial/unavailable states. Financial report results, coverage status and reliability reasons must agree. Keep score policy centralized, explainable, versioned and covered by tests; the UI must never imply statistical probability or completeness of undisclosed assets.


---

## 14. Overlapping statements, duplicate transactions, and synthetic reconciliation adjustments (v0.6, MVP requirement)

### 14.1 Why these belong together

The same user may import statements with **overlapping coverage** (duplicate source events), **gaps** (missing events), or **changed bank exports** (pending versus booked, corrections, different fields). Imported activity, source-reported balances, and user-confirmed balances are different types of evidence. Treat all three separately.

**Product principle:** Matapan may repair a **reconstructed ledger balance** with an explicitly accepted synthetic difference, but must never invent a real purchase, salary or transfer. User confirmation establishes a **dated balance checkpoint**, not a complete historical transaction record. An adjustment does not upgrade historical transaction completeness.

### 14.2 Import identity and overlap: four scopes

1. **File instance:** compute `sha256(file_bytes)` after upload and associate with target account/import scope and parser ID/version. Recognize exact repeat uploads immediately and offer "Already imported". A different file hash is **not** proof of new transactions, and an identical file imported into a different correctly mapped account may be a distinct import candidate requiring review.
2. **Source record:** when a provider offers a stable reliable transaction identifier, use a scoped key such as `(institution, source_account_identity, event_type, provider_record_id)`. Do not assume generic descriptions, local row numbers or timestamps are unique bank IDs. A source ID that changes between pending and booked variants requires explicit parser rules.
3. **Cross-file normalized record:** for providers without reliable IDs, build stable **candidate-matching fields**, including mapped account, currency, signed amount, booking date, normalized original description, optional counterparty/reference, and additional supported identifiers. Persist normalized source data separately from user-edited display fields. A fingerprint from these fields supports candidate discovery, **not an unconditional uniqueness constraint**: legitimate same-day identical purchases exist.
4. **Observation identity:** cash balance snapshots and holdings snapshots are observations, not additive movements. If two files give the same account/currency/as-of balance, deduplicate equivalent observations; if values differ, create a **conflict** for review. A duplicate statement balance must never add a second bank balance to net worth.

Deduplication scope is **account + currency + event type + source** as appropriate. Do **not** merge an outgoing payment on a bank account with an Alipay/WeChat event on a wallet or a destination account's incoming leg solely because amount/date match: those may be separate real ledger legs or payment-provider views of one purchase. Cross-account transfer and payment-source linking are later explicit workflows.

### 14.3 Deterministic preview classification

Every normalized import row receives an initial classification:

| Status | Evidence | User experience / commit behavior |
| --- | --- | --- |
| `new` | No matching persisted event/observation | Accept by default after validation |
| `duplicate` | Trusted scoped provider ID or otherwise **proven** same source record | Skip creating a second canonical event; retain provenance of this occurrence |
| `possible_duplicate` | Similar fields or date/amount/description, without conclusive identity | Show both records and evidence; require explicit keep-separate or link-as-duplicate decision |
| `conflict` | Same stable source identity but materially changed amount/status, or disagreeing balance snapshot | Block automatic overwrite; require source-aware correction/review |
| `invalid` | Missing currency/date/amount, invalid mapping, etc. | Reject row with actionable explanation |

Default **ambiguous** outcomes to **not importing the ambiguous row until reviewed**, not silent discarding and not automatic duplication. For an import of thousands of records, group equivalent candidate issues, provide bulk decisions only where defensible, and leave unaffected rows available for import in a controlled atomic commit of the approved plan. Commit must revalidate identities against current DB state to avoid duplicate creation after a second preview/import.

**User decision persistence:** store the reviewed pair/group, source row IDs, chosen action, decision time and actor, and keep it reversible. Linking as duplicate must retain both `ImportRow` occurrences pointing at **one canonical transaction**. Explicit keep-separate means genuinely separate canonical transactions even with equal fingerprints. Future imports should honor prior decisions for the same verified source identities but should not extrapolate one ambiguity decision to all superficially similar future transactions.

### 14.4 Import periods are evidence, not a uniqueness key

Store per `ImportBatch` the provider-declared `period_start`, `period_end`, export generation time, included account/currency/product and the actual **observed min/max transaction dates** separately; these are not interchangeable. Overlapping periods trigger candidate lookup but should not cause "skip entire month" logic. A gap in coverage may produce a warning, but no claim of missing *individual* transactions unless evidence such as running balances, sequence numbers or an external coverage guarantee supports it.

Use a stable **booking/posted date** convention for transaction order and reconciliation; retain value date, pending state and original timestamp separately if present. Apply consistent inclusive/exclusive boundaries; recommended `(opening_checkpoint_at, closing_checkpoint_at]`, with explicit ordering for multiple intraday events/checkpoints. Date-only balances require source-specific end-of-day semantics; ambiguous boundaries block automatic reconciliation.

### 14.5 Reconciliation-adjustment design (user-approved phantom transactions)

A reconciliation compares two **dated checkpoints in the same account and currency**, using the accepted real movement set **exactly once**:

```text
expected_close = confirmed_open + sum(accepted_real_booked_movements)
               + sum(active_prior_synthetic_adjustments_in_interval)

difference = confirmed_close - expected_close
```

Before offering an adjustment, explicitly show: opening balance/date, closing balance/date, source identity, covered statement intervals, duplicate decisions, movement count, pending/excluded events, expected close, user-confirmed close, difference, and any uncertain date boundary.

When `difference != 0`, offer:

- **Investigate:** leave it unresolved; keep existing checkpoints and show the discrepancy.
- **Accept adjustment:** create one **explicitly synthetic** signed adjustment for the reconciliation period in the account's native currency, recording the effective date, opening and closing checkpoints, amount, explanation and the user's approval timestamp.
- **Request missing statement:** postpone the adjustment while showing the missing interval if known.

When statement coverage is known incomplete, label the adjustment **unexplained / gap compensation**, not "proof" that the underlying events happened in this form. A user-approved synthetic record is **excluded from income, expenses, merchant analysis, trade performance and transfer detection**. It is visible in the account's reconciliation/activity view with its distinct type.

**Critical reporting invariant:** For an as-of date with a selected authoritative balance observation, use that **selected balance** for the cash component of net worth. Never compute `net worth cash = confirmed closing snapshot + synthetic adjustment`. The adjustment only affects **ledger roll-forward projections/reconciliation** between observations. If a downstream roll-forward includes the accepted adjustment, distinguish its derived status from the sourced checkpoint. An accepted synthetic adjustment cannot make an incomplete statement interval factually complete.

### 14.6 Lifecycle when missing records arrive later

When a newly imported statement overlaps or fills a period already reconciled with an adjustment:

1. Deduplicate new movements first and **only** add approved new canonical real events.
2. Find all affected reconciliation periods/checkpoints and active adjustments.
3. Recalculate the expected closing balance using the updated real-event set and the existing adjustment as a separate component.
4. Compute the **new required adjustment** as `confirmed_close - (confirmed_open + unique_real_movements + other_active_adjustments)`; avoid circularly including the adjustment being revised in its own target calculation.
5. Compare old and new required adjustments, then show the user **a proposed reduction, replacement or reversal** and impact on activity completeness and derived balances.
6. Do **not** silently delete/rewrite the previous approved adjustment. Require confirmation to supersede/reverse it and preserve the full audit history. Until review, flag the reconciliation as `needs_review` and avoid presenting the **derived** balance as newly reconciled. The originally confirmed checkpoint stays valid for its historical date unless independently challenged.

**Example (illustrative):** A user accepted `+1,800 SEK` to reconcile a missing interval. A later statement imports a *new, nonduplicate* `+1,200 SEK` movement from that interval. Matapan proposes reducing the unexplained adjustment to `+600 SEK`. If the remaining `+600 SEK` later arrives, propose reversing the adjustment to zero. Do not rewrite real records or treat adjustments as ordinary income.

If a user reverses an adjustment voluntarily, preserve the adjustment and a reversal/supersession record (append-only financial history) and recompute the affected projection. Avoid physical deletion of source evidence or confirmed snapshots.

### 14.7 Database additions and constraints

Implement with normal relational tables, not a generalized plugin or event-sourcing infrastructure:

**`Transaction` (minimal MVP representation for supported bank movements):** internal `id`, `account_id`, `currency_code`, signed `amount`, `posted_at` or source-specific booking date, optional `value_date`, `source_event_id?`, immutable normalized source fields/fingerprint, record state (`booked`, `pending`, `reversed` where supported), `first_import_row_id`, timestamps. Later add category and advanced analytics without changing original source identity. Protect unique **trusted** provider IDs within their proper source scope; do **not** use a unique constraint on amount/date/description alone.

**`ImportRow` extended fields:** canonical `transaction_id?` or other typed record reference, matching classification, matching evidence, selected decision, and link to each occurrence; a join table can preserve many-import-rows-to-one-transaction provenance. Implement reference integrity via real foreign keys where possible.

**`DuplicateDecision` (small audit table):** id, import_row_id, existing_transaction_id, decision (`link_duplicate`, `keep_separate`), reason, user_decided_at, superseded/reversed metadata if necessary.

**`BalanceConfirmation`:** keep per account, currency, as-of date, original/source observation, user decision, confirmation timestamp. Do not overwrite imported observations.

**`Reconciliation` or `ReconciliationPeriod`:** id, account_id, currency_code, opening_balance_observation_id, closing_balance_observation_id, interval start/end, coverage status, evaluation version, state (`open`, `reconciled`, `unresolved`, `needs_review`), creation/update timestamps. Expected/difference totals can be computed on demand; freeze a decision-time calculation snapshot for audit.

**`ReconciliationAdjustment`:** id, reconciliation_id, account_id, currency_code, signed_amount, effective_at, reason/code, user_approved_at, state (`active`, `superseded`, `reversed`), replacement_adjustment_id?, immutable original difference/evidence reference, actor/decision note. Require approval for creation and reversal. Enforce consistent account/currency/checkpoint boundaries.

**Useful indexes:** `(account_id, posted_at)`, scoped trusted provider record IDs, `(account_id, currency_code, normalized_fingerprint)`, `(account_id, currency_code, snapshot_date)` for balances, `(account_id, period_start, period_end)` for imports, and reconciliation interval indices. Index design follows actual query plans, not speculative performance optimization.

**No duplicate cash:** If one reconciliation adjustment spans the same period as another, carefully avoid counting it twice. At most one **active accepted adjustment per disjoint reconciliation unit** unless the system explicitly supports and tests non-overlapping subintervals. Prefer canonical non-overlapping checkpoint intervals for MVP; defer complex interval splitting.

### 14.8 Frontend flow

**Import preview:** display account/currency, declared statement dates, previously imported coverage, a concise tally of **new / skipped duplicates / possible duplicates / conflicts / invalid**, plus expandable matching source evidence. The user resolves uncertain matches before commit. Allow abort and safe re-preview.

**Reconciliation step:** after commit (or as a preview of its expected consequences), show a timeline of the account and its confirmed balance checkpoints. Show unexplained periods and exact signed differences. Offer **Investigate**, **Confirm balance**, and **Accept synthetic adjustment** actions with explicit explanatory text.

**Dashboard:** report source-backed values and as-of dates first. Distinguish `balance verified`, `ledger reconciled with adjustment`, `history incomplete` and `needs review`. The net-worth reliability index may remain high for a verified closing balance while transaction-history completeness remains low. An adjustment does not eliminate the missing-history warning.

### 14.9 Acceptance tests: gaps, overlaps, and adjustment safety

1. Import Jan–Mar followed by Mar–Jun of the **same account**, where records dated 15–31 Mar occur in both: each proven identical transaction is retained **once**, newly observed Apr–Jun records are added, and both import batches remain auditable.
2. Re-import the second file under another filename: no duplicate canonical records, and no redundant balance snapshots.
3. Same day, merchant, amount and currency for two real independent card payments: **both remain** unless a trusted ID or user review establishes otherwise.
4. Identical reference values in **different accounts/currencies/institutions** do not trigger cross-account auto-merging.
5. Source-pending event later reappears as booked with a changed date/amount: parser-specific rules prevent double counting and demand review when identity is not provable.
6. Source reports one closing balance twice, consistently: one accepted valuation at that as-of date; conflicting reported amounts prompt an explicit selection.
7. A gap is inferred from file date ranges: Matapan flags **coverage uncertainty**, not fabricated missing transaction values.
8. User confirms a dated closing balance differing from roll-forward by `+1,800 SEK` and accepts an adjustment: ledger expected balance reconciles; source observation is preserved; no income/expense is created; net worth does **not** count the adjustment on top of the balance.
9. Later import brings a valid `+1,200 SEK` movement into that interval: proposal changes unexplained adjustment from `+1,800` to `+600`; no automatic rewriting; history completeness remains marked partial if still uncertain.
10. Later import brings the final `+600 SEK`: propose reversal of residual adjustment; preserve approvals and original synthetic record in audit history.
11. A user chooses `keep_separate` for an ambiguous duplicate: both records persist; later reimport respects the decision for the same source records.
12. Imported source row plus user-edited description still matches source identity on reimport (identity is not taken from mutable display fields).
13. Mixed debit/credit, different currencies, booking/value dates and incomplete opening or closing checkpoints are not reconciled using the wrong arithmetic or dates.
14. Concurrent commits from the same preview cannot insert duplicate canonical records (revalidate in the same database transaction under SQLite constraints).
15. Backups/restores preserve source rows, duplicate decisions, confirmations, adjustments, supersessions and net-worth reproducibility.
16. A user reverses an accepted adjustment and sees the recalculated roll-forward while the original confirmed balance checkpoint remains unchanged.

### 14.10 Codex implementation sequencing and guardrails

- **M0:** Define typed signed movement, dated checkpoint, adjustment and source-identity contracts and test their arithmetic using synthetic fixtures. Confirm no double counting in net-worth aggregation.
- **M1:** Build first bank parser and end-to-end import preview, immutable event identity, trusted-key deduplication and user review of ambiguous overlaps. Support dated source balance and discrepancy display. If feasible, accept a simple single-period adjustment in M1; otherwise implement it at M2.
- **M2 (mandatory before MVP release):** Complete approval, reversal/supersession and late-import re-reconciliation; add broker import and cross-currency net worth. Test all sixteen scenarios above.
- Do not block the MVP on sophisticated AI-based record linkage, universal reconciliation across arbitrary statement structures, or categorization of every bank transaction. For ambiguous bank-specific rules, fail visibly and require review.
- Parser regression tests use **synthetic/anonymized** fixtures matching real export structures; never commit uploaded statements, names, account identifiers or raw descriptions.
- Never silently fill missing financial history, delete corrections, or infer that reconciled == fully explained.

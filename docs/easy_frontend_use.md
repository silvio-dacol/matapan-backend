# Easy frontend guide

Use this guide to create an account, import a Revolut statement, review possible
duplicates, and see your transactions and dated balance. You can also confirm the
actual account balance when you have not imported all your history.

## 1. Start the backend and frontend

For first-time backend installation, follow
[the backend setup instructions](../backend/README.md). You also need Node.js;
version 22.12 or newer is supported by the frontend.

Open a PowerShell terminal at the repository root and start the backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn matapan.main:app --host 127.0.0.1 --port 8000 --reload
```

Keep that terminal running. Open a **second PowerShell terminal at the repository
root** and start the frontend:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Run `npm.cmd ci` on first use and after dependency updates. On later visits, you
can skip that command. Using `npm.cmd` avoids PowerShell restrictions on the
`npm.ps1` wrapper.

Keep both terminals running and open <http://127.0.0.1:5173>. This is the account
workspace; <http://127.0.0.1:8000/docs> is the separate backend API page.

## 2. Create or select an account

If you already created your account, select it in the **Accounts** list. Accounts
created through the backend API appear here too; you do not need to recreate them.

To add an account:

1. Click **Add your first account**, or **Add account** if accounts already exist.
2. Enter an **Account name**, such as `Revolut CHF`.
3. Select **Revolut** as the institution.
4. Enter the statement's three-letter **Currency**, such as `CHF` or `EUR`.
5. Select **Current account** or **Savings** as the **Revolut product**.
6. Click **Create account**.

Each product/currency combination needs a separate account, such as Current CHF,
Current EUR, or Savings CHF. Imports do not create accounts automatically.

Choose **Other institution** to track a different bank's dated cash balance
manually. CSV import currently supports Revolut only.

On a narrow screen, the account list appears above the workspace instead of beside
it. Account switching and adding accounts are disabled while a form or import
review is open; finish or cancel the current action first.

## 3. Preview a Revolut statement

1. Select the account that matches the statement's product and currency.
2. Click **Import statement**.
3. Click **Choose CSV**, or drop the CSV into the upload area.
4. Click **Preview statement**.
5. Review the observed transaction dates, row counts, **Statement notes**, and
   **Source balance evidence**.

Use the [supported English Revolut bank-statement CSV format](importers/revolut/revolut_csv.md).
PDFs and other export layouts are not supported. The upload limit is **10 MiB**.

The observed dates describe the transactions found in the file. They do not prove
that all activity for that period was included. Rows belonging to another product
or currency are excluded from this account's import.

**Preview alone does not accept transactions or balances.** Confirm within
**30 minutes**, using the same browser tab. Avoid reloading or closing the tab
while reviewing; if the preview expires, close it and upload the file again.

## 4. Review rows and possible duplicates

The preview shows these row categories:

| Category | What to do |
|---|---|
| **New** | Accepted as new by default when you confirm; you may explicitly skip it. |
| **Duplicate** | No second movement is created. An already imported file opens the saved-statement view. |
| **Needs review** | Compare the existing candidates and choose a decision. |
| **Invalid** | Read the explanation and explicitly choose **Skip this row** before confirming. |
| **Excluded** | Belongs to another account context or has an unsupported state; will be excluded. |
| **Conflict** | Review the conflicting evidence; it must not silently overwrite saved data. |

For each row marked **Needs review**:

1. Expand **Compare … existing movements** to inspect the matching records.
2. Open that row's decision menu.
3. Choose one of:
   - **Keep as a separate movement** if both payments really happened.
   - **Link to existing match 1** (or another listed match) if it is the same
     movement already saved.
   - **Skip this row** if you do not want to accept it.

Matching dates, descriptions, and amounts do not prove that two payments are the
same. Two legitimate identical payments can remain separate.

Use **Only rows needing a decision** to focus on rows requiring review, and
**Previous** / **Next** to move through the preview. Decisions on other pages are
kept while the preview stays open. Confirmation remains disabled until all
required decisions are complete.

## 5. Confirm or cancel the import

1. Check the source balance evidence, if present. **Save this balance evidence**
   controls whether it is accepted alongside the movements. For equivalent saved
   evidence, the option reads **Retain link to existing balance**.
2. If the balance conflicts with a saved source checkpoint, it cannot be accepted.
   You can still approve the reviewed movements; the existing balance stays saved.
3. Check **I approve these row decisions and the selected balance evidence.**
4. Click **Confirm import**.
5. Read the result, then click **Back to account**.

Click **Cancel import** instead to leave the preview unconfirmed. This does not
add its movements or balance to the account. A saved import cannot be cancelled
through this action.

If another import changes the matching records, Matapan refreshes the preview and
requires you to review and approve the current decisions again. You can also use
**Refresh preview** yourself; it clears the previous choices for a fresh review.

## 6. Read your account activity and dated balance

The **Account cash** panel shows a balance together with its date and status:

| Status | Meaning |
|---|---|
| **Confirmed by you** | You explicitly confirmed the amount for its stated date. |
| **Source reported** | Revolut supplied a running balance at the displayed source-local timestamp; it is not a verified statement-end or end-of-day balance. |
| **Conflicting evidence** | Different balances exist for the same selected date or checkpoint. No amount is selected. |
| **Balance needed** | No usable balance exists on or before the report date. |

Change **Report as of** to inspect a different date. Future observations are
excluded from that report. If the latest usable observation is older, the context
panel explains that it is carried forward and has not been confirmed for the
requested date. Expand **Report notes** for more detail.

**Not available** means unknown or conflicting, not zero. The figure covers this
account's cash and remains a partial financial picture, not complete net worth.

**Account activity** shows accepted transactions across **all dates**, separately
from the report date. Use **Previous** / **Next** to browse 25 records at a time.
Expand a transaction's **source rows** to see the source amount, fee, and import
references. The displayed movement includes the fee.

**Balance evidence** preserves imported observations and your confirmations,
including observations after the report date. Use **Newer** / **Older** to browse
them. These are dated observations, not amounts to add together.

## 7. Confirm the actual balance with incomplete history

You do not need to import every transaction before confirming the actual balance.
You can also do this before importing any statement.

1. Select the account and click **Confirm balance**.
2. Check the actual amount in your bank's app or statement.
3. Enter it in **Actual balance**, using a decimal point and no thousands
   separators, for example `1234.50`. Negative balances such as `-50.00` are allowed.
4. Set **Balance date** to the date the amount represents. It initially uses the
   current report date, so check it before saving.
5. Optionally add a note, such as `Checked in the bank app`.
6. Check **I confirm this is the account balance for the stated date.**
7. Click **Save confirmed balance**.

The report switches to the confirmation date. If the evidence agrees, it shows
**Confirmed by you**. **History coverage unverified** remains visible: confirming
a balance does not fill missing transactions or reconcile the ledger.

If another observation for the same date differs, both observations are preserved
and the report shows **Conflicting evidence**. The current frontend cannot select
which conflicting observation should be authoritative. Repeatedly entering another
amount does not resolve that conflict.

Reconciliation differences and user-approved synthetic adjustments are subsequent
work; the balance confirmation form does not create those adjustments.

## 8. Return later or try a sample

Accounts, confirmed imports, and saved balance observations persist after you close
the browser or stop the servers. The default database is
`backend/data/matapan.sqlite3`, unless you configured another database. Keep that
file to preserve your data.

To stop the local servers, press **Ctrl+C** in each terminal. To return later,
start the backend and frontend again and open <http://127.0.0.1:5173>.

For another statement with the same product and currency, reuse the existing
account and repeat **preview → review → confirm → view**. Reimporting the same file
does not add duplicate movements. Overlapping files may require duplicate review.

To practise with synthetic data, create a separate **Revolut / Current account /
EUR** account and import
[revolut_mixed_products.csv](../backend/tests/fixtures/revolut_mixed_products.csv).
Then import [revolut_overlap.csv](../backend/tests/fixtures/revolut_overlap.csv) to
practise reviewing overlaps. Both files contain invented transactions; keep this
practice account separate from your real accounts.

Keep real financial exports outside the Git repository.

## 9. Common problems

- **The page will not open:** check that the frontend terminal is still running
  and open the printed local address, normally <http://127.0.0.1:5173>.
- **The workspace cannot connect:** start the backend on port 8000, then click
  **Retry connection**. You can check <http://127.0.0.1:8000/health> in the browser.
- **Import statement is disabled:** close any open form or review. Import requires
  a Revolut account with a Current or Savings product; other accounts support
  manual balance confirmations.
- **No rows match the account:** check the selected product and currency against
  the CSV. Use the correct account for those rows.
- **Confirm import is disabled:** resolve every required row decision, check the
  approval box, and make sure the preview has not expired.
- **The frontend port is occupied:** use the already running Matapan frontend, or
  stop your earlier frontend terminal before starting another.

For direct API actions, including deletion of an empty account, see
[the easy backend API guide](easy_backend_api_use.md). Account deletion is not
available in the current frontend.

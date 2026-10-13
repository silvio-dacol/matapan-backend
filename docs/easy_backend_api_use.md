# Easy backend API guide

Use this guide to create an account, import a Revolut statement, and view the saved
transactions and balance through the browser's interactive API page. To use the
account workspace instead, follow [the easy frontend guide](easy_frontend_use.md).

## 1. Start the backend

For first-time installation, follow [the backend setup instructions](../backend/README.md).
After installation, run these PowerShell commands from the repository root:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn matapan.main:app --host 127.0.0.1 --port 8000 --reload
```

Keep that terminal running and open <http://127.0.0.1:8000/docs>.

## 2. Create an account once

If you already created your account, skip to step 3. To find its ID again, expand
**GET `/api/v1/accounts`**, click **Try it out**, then **Execute**.

1. Expand **POST `/api/v1/accounts`** under **Accounts**.
2. Click **Try it out**.
3. Replace the request body with:

   ```json
   {
     "name": "Revolut CHF",
     "institution": "Revolut",
     "currency_code": "CHF",
     "revolut_product": "Current"
   }
   ```

4. Change the name and currency to match your statement. Use `"Savings"` instead
   of `"Current"` for savings.
5. Click **Execute**. A **201 Created** response means success.
6. In **Response body**, copy the account's full `"id"` value.

Each product/currency combination needs a separate account, such as Current CHF,
Current EUR, or Savings CHF. Accounts are not created automatically by imports.
The number after `127.0.0.1:` in a server log is a network port, not an account ID.

## 3. Preview a Revolut CSV

1. Expand **POST `/api/v1/imports/preview`** and click **Try it out**.
2. Paste your **account ID** into `account_id`.
3. Choose your supported Revolut CSV and click **Execute**.
4. Review the rows, counts, warnings, and dated balance evidence. Rows from other
   products or currencies are marked `excluded`.
5. Copy the preview's top-level `"id"` value for the confirmation step.

Preview alone does not accept the transactions. Confirm within **30 minutes**, in
the **same browser**, so the preview's session cookie is preserved. If it expires,
upload the file again.

## 4. Confirm the import

1. Expand **POST `/api/v1/imports/{preview_id}/commit`**.
2. Click **Try it out** and paste the **preview ID** into `preview_id`.
3. If there are no possible duplicates or invalid rows, replace the entire example
   request body with:

   ```json
   {}
   ```

4. Click **Execute** and check for a successful response.

If the preview contains `possible_duplicate` rows, choose a decision for each one:

- `keep_separate`: save it as a separate transaction.
- `link_duplicate`: link it to one of the listed existing candidate transactions.
- `skip`: do not accept the row.

Invalid rows require `skip`. For example, to keep one possible duplicate:

```json
{
  "decisions": [
    {
      "row_id": "PASTE_THE_ACTUAL_PREVIEW_ROW_ID",
      "action": "keep_separate"
    }
  ]
}
```

Replace the placeholder with the actual row ID from the preview, and include a
decision for every row requiring review. Only `link_duplicate` accepts and requires
`transaction_id`; use a listed candidate transaction ID for that action.

If you see `transaction_id is required only for link_duplicate`, remove
`transaction_id` from a `keep_separate` or `skip` decision. The generated example
UUIDs in `/docs` are placeholders, not your saved IDs. A validation error does not
commit the import.

## 5. View saved transactions

1. Expand **GET `/api/v1/accounts/{account_id}/transactions`**.
2. Click **Try it out**.
3. Paste your **account ID**, not the preview ID.
4. Click **Execute** to see the saved transactions.

The default page contains up to 100 transactions. Use `offset` to view later pages,
for example `100` for the second page when `limit` is `100`.

## 6. View the dated balance

1. Expand **GET `/api/v1/accounts/{account_id}/report`**.
2. Click **Try it out** and paste your **account ID**.
3. Enter the date you want to inspect in `as_of`, using `YYYY-MM-DD`, for example
   your statement's last date.
4. Click **Execute**.

Check `amount`, `balance_as_of_date`, `balance_status`, and any `issues`.
An older balance may be marked `carried_forward`. A `null` amount is unavailable,
not zero: the account may lack usable balance evidence or have conflicting evidence.
This report covers the account's cash, not complete net worth.

## 7. Return later or import another statement

Accounts and confirmed imports persist after you close the browser or stop the
backend. The default database is `backend/data/matapan.sqlite3` (unless you configured
a different database). Keep that file to preserve your data.

To return later, start the backend and open `/docs` again. For another statement
from the same product and currency, reuse the existing account and repeat
**preview → review → confirm → view**. Exact-file reimports do not create duplicate
movements; overlapping statements may need duplicate review.

Keep real financial CSV files outside the Git repository.

## 8. Delete an empty account

Use this to remove an account created by mistake before adding any data.

1. Find the account's ID using **GET `/api/v1/accounts`**.
2. Expand **DELETE `/api/v1/accounts/{account_id}`** and click **Try it out**.
3. Paste the account ID. Check that it belongs to the account you want to remove.
4. Click **Execute**. This permanently deletes the empty account.

A **204 No Content** response means the account was deleted; an empty response body
is expected. **404** means the account does not exist. **409 Conflict** means it has
balances, transactions, or import history and cannot be deleted. Cancelled and
expired previews also count as import history. Those records and the account stay
saved. This endpoint does not remove financial data.

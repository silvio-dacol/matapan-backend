import { useEffect, useState } from "react";
import { api, calendarDate, errorMessage, money } from "./api";
import type { Account, Balance, Transaction } from "./api";
import { Notice } from "./Notice";

export function Activity({
  account,
  revision,
}: {
  account: Account;
  revision: number;
}) {
  const [offset, setOffset] = useState(0);
  const [rows, setRows] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    setOffset(0);
  }, [revision]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api
      .transactions(account.id, offset)
      .then((result) => {
        if (active) setRows(result);
      })
      .catch((failure) => {
        if (active) {
          setRows([]);
          setError(errorMessage(failure));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [account.id, offset, revision, retry]);

  return (
    <section className="panel activity-panel" aria-labelledby="activity-title">
      <div className="section-heading">
        <div>
          <span className="eyebrow">YOUR IMPORTED RECORDS</span>
          <h2 id="activity-title">Account activity</h2>
        </div>
        <span className="tag">All dates</span>
      </div>
      <p className="muted compact">
        Accepted movements, with their original source details. This list may
        cover only part of your history.
      </p>
      {error ? (
        <Notice error>
          {error}{" "}
          <button onClick={() => setRetry((value) => value + 1)}>
            Retry activity
          </button>
        </Notice>
      ) : loading ? (
        <p className="loading" role="status">
          Loading activity…
        </p>
      ) : rows.length === 0 ? (
        <div className="empty-state">
          <span className="empty-symbol" aria-hidden="true">
            ↔
          </span>
          <h3>
            {offset
              ? "No more transactions"
              : "Your activity starts with a statement"}
          </h3>
          <p>
            {offset
              ? "Go back to see the previous records."
              : "Import a Revolut CSV to review and save your transactions. A confirmed balance can stand on its own."}
          </p>
        </div>
      ) : (
        <div className="table-scroll">
          <table>
            <caption className="sr-only">
              Imported account transactions, all dates
            </caption>
            <thead>
              <tr>
                <th>Date</th>
                <th>Transaction</th>
                <th className="numeric">Amount</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td className="nowrap">
                    {calendarDate(row.posted_at)}
                    <span className="cell-subtitle">
                      {row.posted_at.slice(11, 16)} · source local time
                    </span>
                  </td>
                  <td>
                    <span className="transaction-description">
                      {row.source_description || "No description"}
                    </span>
                    <span className="cell-subtitle">
                      {row.transaction_type} · {row.product}
                    </span>
                  </td>
                  <td
                    className={`numeric amount ${row.amount.startsWith("-") ? "" : "positive"}`}
                  >
                    {money(row.amount, row.currency_code)}
                  </td>
                  <td>
                    <details>
                      <summary>
                        {row.import_row_ids.length} source{" "}
                        {row.import_row_ids.length === 1 ? "row" : "rows"}
                      </summary>
                      <div className="evidence-details">
                        <p>
                          Source amount:{" "}
                          {money(row.source_amount, row.currency_code)}
                        </p>
                        <p>Fee: {money(row.fee, row.currency_code)}</p>
                        <p>Net movement includes the fee.</p>
                        {row.import_row_ids.map((id) => (
                          <code key={id}>{id}</code>
                        ))}
                      </div>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="pagination">
        <span className="muted">
          {!loading && rows.length > 0
            ? `Records ${offset + 1}–${offset + rows.length}`
            : "25 records per page"}
        </span>
        <div>
          <button
            disabled={loading || offset === 0}
            onClick={() => setOffset((value) => Math.max(0, value - 25))}
          >
            Previous
          </button>
          <button
            disabled={loading || rows.length < 25}
            onClick={() => setOffset((value) => value + 25)}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}

export function BalanceHistory({
  account,
  revision,
}: {
  account: Account;
  revision: number;
}) {
  const [offset, setOffset] = useState(0);
  const [balances, setBalances] = useState<Balance[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    setOffset(0);
  }, [revision]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api
      .balances(account.id, offset)
      .then((result) => {
        if (active) setBalances(result);
      })
      .catch((failure) => {
        if (active) setError(errorMessage(failure));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [account.id, revision, offset, retry]);
  return (
    <section className="panel" aria-labelledby="evidence-title">
      <div className="section-heading">
        <div>
          <span className="eyebrow">PRESERVED OBSERVATIONS</span>
          <h2 id="evidence-title">Balance evidence</h2>
        </div>
      </div>
      <p className="muted compact">
        Original balances and your confirmations, including observations after
        the report date.
      </p>
      {error ? (
        <Notice error>
          {error}{" "}
          <button onClick={() => setRetry((value) => value + 1)}>
            Retry evidence
          </button>
        </Notice>
      ) : loading ? (
        <p role="status" className="loading">
          Loading evidence…
        </p>
      ) : balances.length === 0 ? (
        <p className="muted evidence-empty">
          {offset
            ? "No more balance observations."
            : "No dated balance yet. Import a statement with balance evidence, or confirm the actual balance."}
        </p>
      ) : (
        <ul className="balance-list">
          {balances.map((balance) => (
            <li key={balance.id}>
              <div>
                <strong className="amount">
                  {money(balance.amount, balance.currency_code)}
                </strong>
                <span className="cell-subtitle">
                  {calendarDate(balance.as_of_date)} ·{" "}
                  {balance.status === "user_confirmed"
                    ? "Confirmed by you"
                    : "Revolut running balance"}
                </span>
                {balance.source_timestamp && (
                  <span className="cell-subtitle">
                    {balance.source_timestamp.slice(11)} · source local time
                  </span>
                )}
                {balance.effective_at && (
                  <span className="cell-subtitle">Checkpoint: {balance.effective_at} (entered at UTC{balance.effective_offset})</span>
                )}
                {balance.note && <p className="balance-note">{balance.note}</p>}
              </div>
              <span
                className={`evidence-dot ${balance.source === "manual" ? "confirmed" : ""}`}
                aria-hidden="true"
              />
            </li>
          ))}
        </ul>
      )}
      <div className="pagination">
        <span className="muted">Evidence stays on record</span>
        <div>
          <button
            disabled={loading || offset === 0}
            onClick={() => setOffset((value) => Math.max(0, value - 10))}
          >
            Newer
          </button>
          <button
            disabled={loading || balances.length < 10}
            onClick={() => setOffset((value) => value + 10)}
          >
            Older
          </button>
        </div>
      </div>
    </section>
  );
}

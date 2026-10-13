import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api, ApiError, calendarDate, errorMessage, money } from "./api";
import { Notice } from "./Notice";
import type {
  Account,
  Classification,
  ImportPreview,
  RowDecision,
} from "./api";

const labels: Record<Classification, string> = {
  new: "New",
  duplicate: "Duplicate",
  possible_duplicate: "Needs review",
  invalid: "Invalid",
  excluded: "Excluded",
  conflict: "Conflict",
};

export default function ImportPanel({
  account,
  onClose,
  onCommitted,
}: {
  account: Account;
  onClose: () => void;
  onCommitted: (message: string) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [decisions, setDecisions] = useState<Record<string, RowDecision>>({});
  const [includeBalance, setIncludeBalance] = useState(true);
  const [approved, setApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [page, setPage] = useState(0);
  const [reviewOnly, setReviewOnly] = useState(false);
  const [now, setNow] = useState(Date.now());
  const fileInput = useRef<HTMLInputElement>(null);
  const previewHeading = useRef<HTMLHeadingElement>(null);
  const finalized = preview?.status === "committed";
  const expired = Boolean(
    preview && !finalized && new Date(preview.expires_at).getTime() <= now,
  );
  const unresolved =
    preview?.rows.filter(
      (row) =>
        ["possible_duplicate", "invalid", "conflict"].includes(
          row.classification,
        ) && !decisions[row.id],
    ).length || 0;
  const visibleRows =
    preview?.rows.filter(
      (row) =>
        !reviewOnly ||
        ["possible_duplicate", "invalid", "conflict"].includes(
          row.classification,
        ),
    ) || [];
  const pageRows = visibleRows.slice(page * 20, (page + 1) * 20);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 10_000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    if (preview) previewHeading.current?.focus();
  }, [preview?.id]);
  // The preview lives in this tab. Protect reviewed choices from accidental navigation.
  useEffect(() => {
    if (!preview || finalized) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [preview, finalized]);

  function acceptFile(candidate: File | null) {
    setError("");
    if (candidate && !/\.csv$/i.test(candidate.name)) {
      setError("Choose a Revolut CSV statement.");
      setFile(null);
      return;
    }
    if (candidate && candidate.size > 10 * 1024 * 1024) {
      setError("The statement must be 10 MiB or smaller.");
      setFile(null);
      return;
    }
    setFile(candidate);
  }

  function showPreview(result: ImportPreview) {
    setPreview(result);
    setDecisions({});
    setApproved(false);
    setIncludeBalance(result.balance?.classification !== "conflict");
    setNow(Date.now());
    setPage(0);
    setReviewOnly(false);
    if (result.already_imported)
      onCommitted(
        "This statement was already imported. No new movements were created.",
      );
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || busy) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      showPreview(await api.preview(account.id, file));
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setBusy(false);
    }
  }

  async function refresh() {
    if (!preview) return;
    setBusy(true);
    setError("");
    try {
      showPreview(await api.refreshPreview(preview.id));
      setMessage(
        "Preview refreshed. Review the current candidates and confirm your choices again.",
      );
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setBusy(false);
    }
  }

  async function commit() {
    if (!preview || busy || expired || unresolved || !approved) return;
    setBusy(true);
    setError("");
    try {
      const result = await api.commit(
        preview.id,
        Object.values(decisions),
        includeBalance,
      );
      setPreview({ ...preview, status: "committed", already_imported: true });
      const summary = result.already_imported
        ? "This statement was already imported. No new movements were created."
        : `Import complete. ${result.new_transactions} new movements, ${result.linked_duplicates} linked duplicates, ${result.skipped_rows} skipped rows. ${result.balance_id ? "Dated balance evidence saved." : "No new balance evidence saved."}`;
      setMessage(summary);
      onCommitted(summary);
    } catch (failure) {
      setApproved(false);
      setError(errorMessage(failure));
      if (failure instanceof ApiError && failure.status === 409) {
        // Never reuse decisions after the server reports a changed matching set.
        setDecisions({});
        try {
          showPreview(await api.refreshPreview(preview.id));
        } catch (refreshFailure) {
          setError(`${errorMessage(failure)} ${errorMessage(refreshFailure)}`);
        }
        setMessage(
          "The import was not confirmed. Review the refreshed preview before trying again.",
        );
      }
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    if (busy) return;
    if (!preview || finalized || expired) {
      onClose();
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.cancel(preview.id);
      onClose();
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 410) onClose();
      else setError(errorMessage(failure));
    } finally {
      setBusy(false);
    }
  }

  function decide(rowId: string, value: string) {
    setApproved(false);
    setDecisions((previous) => {
      const next = { ...previous };
      if (!value) delete next[rowId];
      else if (value.startsWith("link:"))
        next[rowId] = {
          row_id: rowId,
          action: "link_duplicate",
          transaction_id: value.slice(5),
        };
      else
        next[rowId] = {
          row_id: rowId,
          action: value as "keep_separate" | "skip",
        };
      return next;
    });
  }

  return (
    <section className="panel import-panel" aria-labelledby="import-title">
      <div className="section-heading">
        <div>
          <span className="eyebrow">REVOLUT CSV IMPORT</span>
          <h2 id="import-title" tabIndex={-1} ref={previewHeading}>
            {finalized
              ? "Statement saved"
              : preview
                ? "Review before you import"
                : "Bring your activity into view"}
          </h2>
        </div>
        <span className="tag">
          {account.revolut_product} · {account.currency_code}
        </span>
      </div>
      <ol className="import-steps" aria-label="Import progress">
        {["Upload", "Review", "Confirm"].map((step, index) => (
          <li
            key={step}
            className={
              index === (finalized ? 2 : preview ? 1 : 0) ? "current" : ""
            }
            aria-current={
              index === (finalized ? 2 : preview ? 1 : 0) ? "step" : undefined
            }
          >
            <span>{index + 1}</span>
            {step}
          </li>
        ))}
      </ol>
      {error && <Notice error>{error}</Notice>}
      {message && (
        <div className="notice" role="status">
          {message}
        </div>
      )}
      {!preview ? (
        <form onSubmit={upload}>
          <fieldset disabled={busy}>
            <div
              className="upload-zone"
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                if (!busy) acceptFile(event.dataTransfer.files[0] || null);
              }}
            >
              <span className="upload-symbol" aria-hidden="true">
                ↥
              </span>
              <h3>{file ? file.name : "Choose your Revolut statement"}</h3>
              <p>Drop a CSV here, or select it from your computer.</p>
              <label className="file-picker">
                Choose CSV
                <input
                  ref={fileInput}
                  type="file"
                  accept=".csv,text/csv"
                  aria-label="Choose Revolut CSV"
                  onChange={(event) =>
                    acceptFile(event.target.files?.[0] || null)
                  }
                />
              </label>
              <span className="form-note">
                English bank-statement CSV · Up to 10 MiB
              </span>
            </div>
            <p className="muted compact">
              Only {account.revolut_product} / {account.currency_code} rows will
              be accepted for this account. You will review the results before
              financial data is saved.
            </p>
            <div className="button-row">
              <button className="primary" type="submit" disabled={!file}>
                {busy ? "Reading statement…" : "Preview statement"}
              </button>
              <button type="button" onClick={() => void cancel()}>
                Cancel
              </button>
            </div>
          </fieldset>
        </form>
      ) : finalized ? (
        <div className="import-success">
          <span className="success-symbol" aria-hidden="true">
            ✓
          </span>
          <h3>
            {message
              ? "Your account view is up to date."
              : "This statement has already been saved."}
          </h3>
          <p className="muted">
            Repeated imports do not create new copies of the same file’s
            movements. The account report below shows the dated evidence.
          </p>
          <button className="primary" onClick={onClose}>
            Back to account
          </button>
        </div>
      ) : (
        <>
          <div className="import-context">
            <p>
              <strong>{file?.name || "Revolut statement"}</strong>
              <span className="cell-subtitle">
                Observed transactions: {calendarDate(preview.observed_start)} –{" "}
                {calendarDate(preview.observed_end)}. These are observed dates,
                not a verified statement period.
              </span>
            </p>
            <button onClick={() => void refresh()} disabled={busy || expired}>
              Refresh preview
            </button>
          </div>
          <div className="review-counts">
            {(
              [
                "new",
                "duplicate",
                "possible_duplicate",
                "invalid",
                "excluded",
                "conflict",
              ] as Classification[]
            ).map((status) => (
              <div key={status}>
                <strong>{preview.counts[status] || 0}</strong>
                <span>{labels[status]}</span>
              </div>
            ))}
          </div>
          <details className="warning-details">
            <summary>Statement notes ({preview.warnings.length})</summary>
            <ul>
              {preview.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </details>
          {preview.balance ? (
            <div
              className={`balance-preview ${preview.balance.classification === "conflict" ? "has-conflict" : ""}`}
            >
              <div>
                <span className="eyebrow">SOURCE BALANCE EVIDENCE</span>
                <strong className="amount">
                  {money(preview.balance.amount, preview.currency_code)}
                </strong>
                <p>
                  {calendarDate(preview.balance.as_of_date)} at{" "}
                  {preview.balance.source_timestamp.slice(11)} · source local
                  time
                </p>
                <p className="form-note">
                  This is a running balance, not a verified end-of-day or
                  statement-end balance.
                </p>
              </div>
              <label className="check-label">
                <input
                  type="checkbox"
                  checked={includeBalance}
                  disabled={
                    busy || preview.balance.classification === "conflict"
                  }
                  onChange={(event) => {
                    setIncludeBalance(event.target.checked);
                    setApproved(false);
                  }}
                />
                {preview.balance.classification === "duplicate"
                  ? "Retain link to existing balance"
                  : "Save this balance evidence"}
              </label>
              {preview.balance.classification === "conflict" && (
                <p className="conflict-explanation">
                  This differs from saved evidence for the same source
                  checkpoint. Only reviewed movements can be imported; the
                  conflicting balance will not be accepted. The existing
                  observation stays unchanged.
                </p>
              )}
            </div>
          ) : (
            <div className="subtle-note">
              No trustworthy closing balance was established. Importing these
              movements will not invent a balance. You can confirm the actual
              dated balance separately.
            </div>
          )}
          <div className="review-toolbar">
            <h3>Review statement rows</h3>
            <label className="check-label">
              <input
                type="checkbox"
                checked={reviewOnly}
                onChange={(event) => {
                  setReviewOnly(event.target.checked);
                  setPage(0);
                }}
              />
              Only rows needing a decision
            </label>
          </div>
          <div className="table-scroll">
            <table className="preview-table">
              <caption className="sr-only">
                Statement preview and import decisions
              </caption>
              <thead>
                <tr>
                  <th>Row / date</th>
                  <th>Source record</th>
                  <th className="numeric">Movement</th>
                  <th>Status & decision</th>
                </tr>
              </thead>
              <tbody>
                {pageRows.map((row) => {
                  const decision = decisions[row.id];
                  const value =
                    decision?.action === "link_duplicate"
                      ? `link:${decision.transaction_id}`
                      : decision?.action || "";
                  return (
                    <tr key={row.id}>
                      <td>
                        #{row.row_number}
                        <span className="cell-subtitle">
                          {row.posted_at
                            ? calendarDate(row.posted_at)
                            : "Missing date"}
                        </span>
                        {row.posted_at && (
                          <span className="cell-subtitle">
                            {row.posted_at.slice(11, 19)}
                          </span>
                        )}
                      </td>
                      <td>
                        <span className="transaction-description">
                          {row.description || "No description"}
                        </span>
                        <span className="cell-subtitle">
                          {row.product || "Unknown product"} ·{" "}
                          {row.currency_code || "Unknown currency"} ·{" "}
                          {row.source_state}
                        </span>
                        {row.errors.length > 0 && (
                          <ul className="row-errors">
                            {row.errors.map((reason) => (
                              <li key={reason}>{reason}</li>
                            ))}
                          </ul>
                        )}
                        {row.candidate_transactions.length > 0 && (
                          <details className="candidate-details">
                            <summary>
                              Compare {row.candidate_transactions.length}{" "}
                              existing{" "}
                              {row.candidate_transactions.length === 1
                                ? "movement"
                                : "movements"}
                            </summary>
                            <ul>
                              {row.candidate_transactions.map(
                                (candidate, index) => (
                                  <li key={candidate.id}>
                                    <strong>
                                      Match {index + 1}: {candidate.description}
                                    </strong>
                                    <span>
                                      {calendarDate(candidate.posted_at)}{" "}
                                      {candidate.posted_at.slice(11, 19)} ·{" "}
                                      {money(
                                        candidate.amount,
                                        row.currency_code,
                                      )}
                                    </span>
                                    <code>{candidate.id}</code>
                                  </li>
                                ),
                              )}
                            </ul>
                            <p>
                              Matching fields do not prove these are the same
                              payment.
                            </p>
                          </details>
                        )}
                      </td>
                      <td className="numeric amount">
                        {row.amount === null
                          ? "Unavailable"
                          : money(row.amount, row.currency_code)}
                      </td>
                      <td>
                        <span className={`row-status ${row.classification}`}>
                          {labels[row.classification]}
                        </span>
                        {row.classification === "excluded" ||
                        row.classification === "duplicate" ? (
                          <span className="cell-subtitle">
                            {row.classification === "excluded"
                              ? "Will be excluded"
                              : "No new movement"}
                          </span>
                        ) : (
                          <select
                            aria-label={`Decision for row ${row.row_number}`}
                            value={value}
                            disabled={busy || expired}
                            onChange={(event) =>
                              decide(row.id, event.target.value)
                            }
                          >
                            <option value="">
                              {row.classification === "new"
                                ? "Import as new (default)"
                                : "Choose a decision…"}
                            </option>
                            {(row.classification === "new" ||
                              row.classification === "possible_duplicate") && (
                              <option value="keep_separate">
                                Keep as a separate movement
                              </option>
                            )}
                            {row.candidate_transactions.map(
                              (candidate, index) => (
                                <option
                                  key={candidate.id}
                                  value={`link:${candidate.id}`}
                                >
                                  Link to existing match {index + 1}
                                </option>
                              ),
                            )}
                            <option value="skip">Skip this row</option>
                          </select>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {pageRows.length === 0 && (
              <p className="muted evidence-empty">No rows match this filter.</p>
            )}
          </div>
          <div className="pagination">
            <span className="muted">
              {visibleRows.length
                ? `${page * 20 + 1}–${Math.min((page + 1) * 20, visibleRows.length)} of ${visibleRows.length} rows`
                : "0 rows"}
            </span>
            <div>
              <button
                disabled={busy || page === 0}
                onClick={() => setPage((value) => value - 1)}
              >
                Previous
              </button>
              <button
                disabled={busy || (page + 1) * 20 >= visibleRows.length}
                onClick={() => setPage((value) => value + 1)}
              >
                Next
              </button>
            </div>
          </div>
          <div className="commit-section">
            {expired && (
              <Notice error>
                This preview has expired. Close it and upload the file again to
                review a fresh plan.
              </Notice>
            )}
            <p className="review-remaining" role="status">
              {unresolved
                ? `${unresolved} ${unresolved === 1 ? "row needs" : "rows need"} your decision before import.`
                : "All required row decisions are complete."}
            </p>
            <label className="check-label">
              <input
                type="checkbox"
                checked={approved}
                disabled={busy || expired || unresolved > 0}
                onChange={(event) => setApproved(event.target.checked)}
              />
              I approve these row decisions and the selected balance evidence.
            </label>
            <div className="button-row">
              <button
                className="primary"
                disabled={busy || expired || unresolved > 0 || !approved}
                onClick={() => void commit()}
              >
                {busy ? "Working…" : "Confirm import"}
              </button>
              <button disabled={busy} onClick={() => void cancel()}>
                {expired ? "Close expired preview" : "Cancel import"}
              </button>
              <span className="form-note">
                Preview expires{" "}
                {new Intl.DateTimeFormat("en-GB", {
                  hour: "2-digit",
                  minute: "2-digit",
                  timeZoneName: "short",
                }).format(new Date(preview.expires_at))}
                .
              </span>
            </div>
          </div>
        </>
      )}
    </section>
  );
}

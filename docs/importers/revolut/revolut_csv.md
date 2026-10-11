# Supported Revolut statement variant

Parser: `revolut_bank_csv_en`, version `1`.

The initial adapter was verified against two user-supplied English bank-statement
CSVs. Private source files remain outside Git. Tests use invented fixtures sharing
their structural format; no source amounts, identifiers, or descriptions were copied.

The file must be UTF-8 (an optional BOM is accepted), comma-delimited, and have this
exact header in this order:

```csv
Type,Product,Started Date,Completed Date,Description,Amount,Fee,Currency,State,Balance
```

- `Product` supports `Current` and `Savings`. An account's `revolut_product` and
  currency explicitly determine which rows belong to it. Other contexts are
  excluded, so savings and current-account running balances are never merged.
- `Started Date` and `Completed Date` use `YYYY-MM-DD HH:MM:SS`. A completed date
  is required for a booked movement. Original timestamps are retained without
  inventing a timezone; `Completed Date` is the posted-date convention.
- `Amount`, `Fee`, and non-empty `Balance` must be signed exact decimal text with
  at most 20 integer digits and 8 fractional digits. Fees must be nonnegative in
  this variant. A blank running balance is permitted and remains unknown.
- The signed ledger movement is `Amount - Fee`. This convention was verified
  against consecutive running balances in the supplied samples, including rows
  with non-zero fees. The raw amount and fee are retained separately.
- Only `State: COMPLETED` produces a canonical movement. Pending, reverted, and
  other non-completed rows remain excluded evidence; they do not silently replace
  previously accepted transactions.
- `Type` is retained as a provider category, without classifying financial income
  or expenses. `Description` is immutable source text, capped at 500 characters.
- Limits: 10 MiB per uploaded file and 10,000 transaction rows.

This header has no account identifier, trusted transaction identifier, explicit
statement period, or timezone. The account mapping is supplied by the user.
Observed min/max completed timestamps are stored separately from a declared period
(which remains unknown). Dates in the filename are not treated as source evidence.

Candidate fingerprints use product, currency, category, completed calendar date,
exact net movement, fee, and normalized original description. They are lookup keys,
never uniqueness constraints. Matching rows in another file require an explicit
keep-separate or link-as-duplicate decision. Two independent equal purchases can
coexist. The same bytes for the same account/parser context prove an exact file
reimport and reuse the original decisions.

An import may accept the latest usable source-reported running balance for its
selected context. Its completed timestamp and source row are retained. An ambiguous
latest timestamp with conflicting source balances produces no selected checkpoint.
Missing balances are not reconstructed from partial movement history. A running
balance is an observation at that timestamp, not automatically an end-of-day or
statement-end balance. Reports show that distinction and mark tracked cash as
partial; they do not claim complete net worth or complete transaction coverage.

# Database Entity-Relationship Diagram

## Entity-Relationship Diagram (Mermaid)

```mermaid
erDiagram
    Currency {
        string code PK "ISO 4217 (EUR, CHF, SEK...)"
        string name "Full name"
        string symbol "€, $, ¥..."
        int decimal_places "Usually 2"
    }

    FxRate {
        int id PK
        date date "Daily rate"
        string from_currency_code FK
        string to_currency_code FK
        decimal rate "10 decimal places"
        string source "API source"
    }

    Institution {
        int id PK
        string name "Revolut, SEB..."
        string country "SE, IT, CN..."
        string parser_name "Which parser to use"
    }

    Account {
        int id PK
        string name "My EUR Account"
        AccountType account_type "checking, savings..."
        string currency_code FK
        int institution_id FK "Optional"
        string account_number "IBAN or account #"
        boolean is_active
    }

    AccountBalance {
        int id PK
        int account_id FK
        date date "Snapshot date"
        decimal balance "Balance on that date"
    }

    Category {
        int id PK
        string name "Groceries, Rent..."
        int parent_id FK "Self-reference for hierarchy"
    }

    Transaction {
        int id PK
        int account_id FK
        date date "Transaction date"
        decimal amount "Original amount"
        string currency_code FK
        TransactionType transaction_type "income, expense..."
        string description "Cleaned description"
        string original_description "From bank statement"
        int category_id FK "Optional"
        decimal amount_in_reporting_currency "Converted to CHF/EUR..."
        decimal fx_rate_used "Rate used for conversion"
        string ticker "For investments"
        decimal quantity "For investments"
        decimal price "For investments"
        string reference_id "Bank's reference"
        boolean is_reconciled
    }

    Tag {
        int id PK
        string name "travel, business..."
    }

    TransactionTag {
        int transaction_id PK, FK
        int tag_id PK, FK
    }

    Asset {
        int id PK
        string name "Apartment, Car..."
        string asset_type "real estate, vehicle..."
        string currency_code FK
        decimal current_value
        decimal purchase_price
        date purchase_date
    }

    Liability {
        int id PK
        string name "Mortgage, Car loan..."
        string liability_type "mortgage, personal..."
        string currency_code FK
        decimal current_value
        decimal original_value
        decimal interest_rate
        date start_date
        date end_date
    }

    ParserMetadata {
        int id PK
        string parser_name "revolut, ib..."
        string file_name "Original filename"
        string file_hash "SHA256 to avoid duplicates"
        datetime parse_date
        int records_imported
        int account_id FK
    }

    %% Relationships
    Currency ||--o{ Account : "has"
    Currency ||--o{ Transaction : "uses"
    Currency ||--o{ FxRate : "from"
    Currency ||--o{ FxRate : "to"
    Currency ||--o{ Asset : "denominated in"
    Currency ||--o{ Liability : "denominated in"

    Institution ||--o{ Account : "has"

    Account ||--o{ Transaction : "contains"
    Account ||--o{ AccountBalance : "tracks"

    Transaction }o--|| Category : "categorized as"
    Transaction }o--o{ Tag : "tagged with"

    Category ||--o{ Category : "parent of"

    FxRate }o--|| Currency : "from"
    FxRate }o--|| Currency : "to"

    Asset }o--|| Currency : "in"
    Liability }o--|| Currency : "in"

    ParserMetadata }o--|| Account : "imported to"
```

## Key Design Decisions

### 1. Multi-Currency Support
- Each **Transaction** stores original `amount` and `currency_code`
- The `amount_in_reporting_currency` field stores the FX-converted value (e.g., to CHF)
- Daily **FxRate** table stores historical rates for accurate conversion

### 2. Transaction Categorization
- **Category** supports hierarchy via `parent_id` (e.g., "Food" → "Groceries")
- **Tag** provides flexible many-to-many labeling
- Category is optional (AI can suggest later)

### 3. Investment Tracking
- **Transaction** has `ticker`, `quantity`, `price` for securities
- **AccountType.INVESTMENT** distinguishes investment accounts

### 4. Net Worth Calculation
- **AccountBalance** snapshots balances over time for historical net worth
- **Asset** and **Liability** tables for real-world holdings

### 5. Parser Metadata
- **ParserMetadata** tracks imports to avoid duplicate processing
- `file_hash` allows detecting if same file is re-uploaded

## Normalization Notes

| Principle | How It's Applied |
|-----------|------------------|
| 1NF | Each field contains atomic values |
| 2NF | All non-PK fields depend on full PK in TransactionTag (composite PK) |
| 3NF | No transitive dependencies; Currency code is PK, not repeated |

## Indexes for Performance

- `FxRate.date` - Quick FX lookup by date
- `Transaction.account_id` + `Transaction.date` - Fast account history
- `AccountBalance.account_id` + `AccountBalance.date` - Balance history
- `Transaction.category_id` - Category filtering

## Questions to Consider

1. Should `FxRate` have a composite unique constraint on (date, from_currency, to_currency)?
2. Do we need soft delete for Transactions (is_deleted flag)?
3. Should we track balance snapshots automatically or on-demand?

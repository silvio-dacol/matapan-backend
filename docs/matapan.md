Yes. Here’s the useful summary of what we established in this conversation, focusing on the Matapan database/ERD work.

Matapan: database design

You are building Matapan, a Rust based financial analyst for expats. The goal is to import financial data from different institutions and countries into one local database, then use it to analyze:

Net worth
Cash flow
Spending
Investments
Asset/liability evolution
Inflation adjusted wealth
Multi currency finances

The database is intended to support Italy, Sweden, China and other countries/institutions over time.

Core design principle

We separated the data into three conceptual types:

1. Entities / things
These represent things that exist:

Currency
Institution
Account
Category
Security
Asset
Liability

2. Events
These represent things that happened:

Transaction
Trade
Import

3. Historical observations
These represent how something changed over time:

AccountBalance
PositionSnapshot
AssetValue
LiabilityBalance
SecurityPrice
FxRate
PriceIndex

This was the main structural improvement over the original ERD.

Important decisions we made
Account balance

We decided not to keep current_balance directly in Account.

Instead:

Account
    ↓
AccountBalance
    ↓
historical snapshots

This means you can reconstruct the account's balance at different dates.

A unique constraint should exist on:

(account_id, snapshot_date)

This also avoids having two competing sources of truth.

Net worth

We decided not to initially create a NetWorthSnapshot table.

Instead, calculate net worth from the underlying data:

Net Worth =
    Account balances
  + Investment positions × market prices
  + Asset values
  − Liability balances

Everything gets converted to the reporting currency using FxRate.

This keeps the database normalized and means you can change your calculation logic later without having to rebuild historical net worth records.

Investments

We separated:

Trade

from:

PositionSnapshot

A Trade answers:

What happened?

For example:

BUY 10 AAPL at $200

A PositionSnapshot answers:

What did I own at this point in time?

For example:

2026-09-30
AAPL
quantity = 50
price = $210
market_value = $10,500

This is important because trades alone aren't necessarily enough to reconstruct historical portfolio state efficiently.

We also added:

SecurityPrice

for historical market prices.

Assets

An Asset represents the actual thing:

Apartment
Car
Other asset

while:

AssetValue

stores how its value changes over time.

So:

Asset
  ↓
AssetValue

rather than constantly overwriting current_value.

Liabilities

Same principle:

Liability
  ↓
LiabilityBalance

For example:

Mortgage
    ↓
2026-01-01 → CHF 400,000
2026-02-01 → CHF 398,500
2026-03-01 → CHF 397,000
Inflation

We discussed how to represent inflation.

Instead of storing something called InflationRate, we chose:

PriceIndex

because the underlying CPI/HICP index is the actual source data.

Example:

PriceIndex
────────────────────────
country_code
index_code
series_code
date
index_value
source

Then inflation can be calculated:

Inflation =
(Index_current / Index_previous - 1) × 100

This avoids storing redundant derived data.

It also allows Matapan to calculate things such as:

My CHF 500k net worth in 2015 had what purchasing power in 2026?

FX

We kept FX as a time series:

FxRate

with:

from_currency
to_currency
date
rate
source

Unique constraint:

(from_currency_code, to_currency_code, date)

You previously decided that daily FX rates make more sense for Matapan than using a monthly “month before” rate.

Current ERD tables

The latest design contains 20 tables:

Configuration / reference
Currency
UserSettings
Institution
Category
Banking
Account
AccountBalance
Transaction
Tag
TransactionTag
Investments
Security
Trade
PositionSnapshot
SecurityPrice
Other wealth
Asset
AssetValue
Liability
LiabilityBalance
Economic / external data
FxRate
PriceIndex
Import
Import
Relationships

The major relationships are:

Currency
 ├── Account
 ├── Transaction
 ├── Security
 ├── Asset
 ├── Liability
 ├── FxRate
 ├── SecurityPrice
 └── UserSettings

Institution
 └── Account

Account
 ├── AccountBalance
 ├── Transaction
 ├── Trade
 ├── PositionSnapshot
 └── Import

Category
 ├── Category          ← self reference
 └── Transaction

Transaction
 └── TransactionTag
       └── Tag

Security
 ├── Trade
 ├── PositionSnapshot
 └── SecurityPrice

Asset
 └── AssetValue

Liability
 └── LiabilityBalance
One important unresolved design point

We flagged transfers between your own accounts as something that needs careful treatment.

For example:

SEB → Revolut
CHF 2,000

This should not become:

CHF 2,000 income
+
CHF 2,000 expense

because your net worth hasn't changed.

So Matapan eventually needs a good way to distinguish genuine income/expenses from internal transfers.

That is probably one of the next database design questions worth resolving.
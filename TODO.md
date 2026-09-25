Matapan

A local first financial analyst for expats, designed to consolidate financial data from multiple banks and countries into one coherent system.

1. Main goal

Matapan should:

Import bank statements from different institutions
Parse and normalize transactions
Support multiple currencies
Calculate net worth and cash flow
Apply FX rates consistently
Categorize transactions, potentially using local AI
Store the user's financial data locally
Eventually provide a clean web interface for analysis

The initial countries of interest are Italy, Sweden, Switzerland, and China, with the architecture designed to be extensible.

2. Frontend and Backend

We decided that the application should have two repositories:

matapan-backend
matapan-frontend

In particular the backend should be responsible for everything involving financial data and business logic:

Database
Transactions
Accounts
Assets/liabilities
Parsers
Currency conversion
Financial calculations
AI integration
API
Frontend

Responsible primarily for:

Dashboard
Charts
Tables
Transaction views
Import UI
Filters
User interaction

The frontend does not access the database directly.

Instead:

Frontend
   ↓
REST/API
   ↓
Backend
   ↓
Database

This also gives us a clean path to potentially expose Matapan remotely in the future.

3. Database

We moved away from using JSON as the primary database.

The current preferred option is:

SQLite

The actual data would live in something like:

matapan.db

SQLite is particularly appropriate because Matapan is initially a personal/home-server application.

Advantages:

Single database file
No database server to maintain
Transactions and relational queries
Very mature
Easy backup
Excellent for a single-user application
Works well with Docker
Easy to migrate to PostgreSQL later if Matapan grows substantially

JSON is still useful, but primarily for:

Import/export
Data interchange
Backups in a human-readable format

The database itself should not be committed to Git.

The repository contains the database schema and migrations, while the actual financial data stays on the server.

4. Home-server deployment

The architecture works very well for your home server.

Something like:

                    PC / Phone / Tablet
                           │
                           ▼
                  ┌─────────────────┐
                  │    Frontend     │
                  └────────┬────────┘
                           │ API
                           ▼
                  ┌─────────────────┐
                  │     Backend     │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │     SQLite      │
                  │  matapan.db     │
                  └─────────────────┘

                  Optional:
                  ┌─────────────────┐
                  │     Ollama      │
                  └─────────────────┘

Everything can run through Docker/Docker Compose.

For example:

Docker
├── matapan-backend
├── matapan-frontend
├── ollama
└── reverse-proxy

The reverse proxy would only be necessary if you want convenient HTTPS/external access.

5. Rust vs Python

Initially we were leaning toward Rust because of:

Strong typing
Reliability
Performance
Low memory usage
Good long-term maintainability
Self-contained deployment

However, after considering what Matapan actually needs, we reconsidered this.

The important observation is that Python will probably let you develop Matapan faster, while the performance difference is unlikely to matter for a personal financial application.

For example, processing 10,000 transactions is unlikely to be CPU-bound by Python. More significant bottlenecks will probably be:

Bank statement parsing
       ↓
AI classification
       ↓
Database operations
       ↓
FX data

The Ollama calls in particular will generally dominate the time involved in AI-based processing.

Python also has a very strong ecosystem for:

CSV/Excel
PDF processing
pandas
numpy
financial analysis
data manipulation
AI/ML
experimentation

So our current recommendation has shifted toward Python.

6. Current proposed stack

I would currently use:

Frontend
    React
    TypeScript

Backend
    Python
    FastAPI

Database
    SQLite

ORM / database layer
    SQLAlchemy or SQLModel

AI
    Ollama

Deployment
    Docker / Docker Compose

With:

matapan-frontend/
matapan-backend/

as the two Git repositories.

7. Backend architecture

The Python backend could eventually look approximately like:

matapan-backend/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── database/
│   ├── parsers/
│   ├── services/
│   └── ai/
│
├── migrations/
├── tests/
├── Dockerfile
└── pyproject.toml

The important architectural separation remains the same regardless of whether we use Python or Rust.

For example:

API
 │
 ├── Financial services
 │
 ├── Parser system
 │
 ├── AI system
 │
 ├── FX system
 │
 └── Storage
       │
       └── SQLite
8. Parser architecture

The parser system should be extensible rather than having one giant parser.

The original institutions we discussed include:

Revolut
Interactive Brokers
China Construction Bank
Intesa Sanpaolo
SEB
Alipay / WeChat utilities
A general AI-assisted parser for unsupported formats

The idea is essentially:

Input file
    ↓
Identify / select parser
    ↓
Parse
    ↓
Normalize
    ↓
Validate
    ↓
Database

Every institution can have its own parser while producing the same internal transaction model.

9. Multi-currency

Matapan needs to treat currency as a first-class property of financial data.

For example:

Account A → CHF
Account B → EUR
Account C → SEK
Account D → CNY

Transactions retain their original currency and original amount.

For consolidated analysis, Matapan converts values into a chosen reporting currency.

We decided to use daily FX rates, rather than a monthly rate, because it provides consistency and more accurate historical valuation.

Conceptually:

Transaction
    amount: 100
    currency: EUR
    date: 2026-09-10

        ↓ daily FX rate

Reporting currency: CHF
    amount: ~93 CHF

The original transaction should remain untouched.

10. AI

AI should be an additional component rather than something the entire backend depends on.

The original idea was to use local Ollama for transaction parsing/classification.

This keeps sensitive financial information local.

The architecture should therefore allow:

Parser
   ↓
AI service
   ↓
Ollama

while still allowing deterministic parsers to work without AI.

11. Important architectural principle

The most important decision isn't actually Python vs Rust.

It is the separation:

Frontend
   │
   │ API
   ▼
Backend
   │
   ├── Financial logic
   ├── Parsers
   ├── AI
   ├── FX
   └── Database

This means the implementation language can change without destroying the overall architecture.

So if Matapan starts in Python and some component later needs Rust, we can replace that component without redesigning the entire application.

Current target

If we freeze the decisions today, I'd describe Matapan as:

A local-first financial analysis application with a React/TypeScript frontend, Python/FastAPI backend, SQLite database, local Ollama AI, extensible financial-data parsers, multi-currency support, and Docker-based deployment on a home server.

That is the architecture I would use as the baseline before starting implementation.

12. Database migrations

Never assume the database schema will remain unchanged.

Use Alembic for migrations. Each migration should be atomic and reversible.

Example migration sequence:

migration 001
    currencies
    institutions

migration 002
    accounts

migration 003
    transactions

migration 004
    categories

migration 005
    tags

migration 006
    budgets

migration 007
    assets
    liabilities

migration 008
    ADD merchant TO transactions

When releasing a new version:

Old database
     ↓
migration
     ↓
New database

The user's existing financial data remains intact.

This is extremely important for a personal application because you don't want an update to destroy someone's historical financial data.

Non-negotiable rules:

Database migrations
Backups before migrations
Actual database never stored in Git
Test migrations on a copy of real data

13. User changes vs developer changes

There are two completely different kinds of "changes":

User changes (no migration required)

For example:

I renamed "Restaurants" to "Eating Out".

UPDATE categories
SET name = 'Eating Out'
WHERE id = 12;

Developer changes (migration required)

For example:

We decided that transactions need a merchant field.

ALTER TABLE transactions ADD COLUMN merchant VARCHAR(200);

This distinction makes the system much easier to maintain.

14. Domain model hierarchy

Design the database around stable financial concepts, not around what the frontend currently looks like.

                    Institution
                         │
                         ▼
                      Account
                         │
                         ▼
                    Transaction
                     /    |    \
                    /     |     \
                   ▼      ▼      ▼
              Category  Currency  Merchant
                                  │
                                  ▼
                                  Tags

Core entities (stable concepts):

Institution
Account
Transaction
Category
Merchant
Tag
Currency
FxRate
Budget
Asset
Liability
ExchangeRate

Additional concepts can be added independently without redesigning the core structure.

15. IDs not names

Always reference entities by ID, never by name.

Good:

transaction.category_id = 42

Bad:

transaction.category = "Food"

If the user changes Food → Restaurants, all transactions remain correctly connected via category_id.

This applies to:

accounts
institutions
categories
tags
currencies
users
assets

16. Audit and classification history

For a financial application, track how transactions got their classification.

transaction
    classification_source: enum(imported, ai, rule, manual)

Suppose you import a transaction:

Uber
CHF 32.50
Transport

Then AI classifies it as:

Travel

Then you manually change it to:

Transport

Matapan can eventually learn that preference:

"I manually changed this merchant to Transport three times."

Matapan could eventually learn that preference and auto-apply it.

Suggested fields on Transaction:

classification_source: imported | ai | rule | manual
classified_by_rule: Optional[str]  -- name of the rule that classified it
ai_confidence: Optional[float]  -- confidence score from AI
original_category_id: Optional[int]  -- category before manual override

This gives much more powerful behavior for automation.

17. Design philosophy: Store facts, compute derivatives

The database should store facts, not derived values.

Store:
    amount (the transaction amount in original currency)
    currency_code (the original currency)
    fx_rate_used (for audit purposes only)

Don't store:
    amount_in_reporting_currency (computed on read)
    unrealized_profit (computed on read)
    market_value (computed on read)
    net_worth_total (computed on read)

Why?
- If you store computed values, you have to update them when:
  - FX rates change
  - User changes reporting currency preference
  - You discover an error in the original data
  - Security prices change

- If you compute on read:
  - Values are always current
  - No stale data
  - Simpler schema
  - Backend does the math, database is the source of truth

The only exception is if you need to store the rate FOR AUDIT purposes
("this is the rate we used for this transaction at import time").

18. Non-negotiable design principles

Database migrations
Stable domain entities
Foreign keys and proper relationships
IDs instead of names as references
Frontend communicates only through the API
Backend owns all financial/business logic
User data separated from schema/versioning
Actual database never stored in Git
Backups before migrations
Keep the schema extensible, but don't make it completely dynamic

The schema should be designed around the financial domain, not around frontend flexibility. Financial concepts like Transaction, Account, Currency, Amount, Date, Category, Institution are stable. Use proper SQL columns and relationships for those.

If you make everything dynamic (entity/key/value), you lose:

type safety
constraints
efficient queries
easy reporting
data integrity

18. Recommended architecture

                  MATAPAN
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
     Frontend Repo         Backend Repo
     React/TypeScript      Python/FastAPI
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
                 Domain       Parsers        AI
                 Logic
                    │
                    ▼
                SQLAlchemy
                    │
                    ▼
                  SQLite
                    │
                    ▼
              matapan.db

The key architectural rules:

React never modifies SQLite directly
FastAPI provides REST API endpoints
Service layer handles business logic
SQLAlchemy/SQLModel handles database access
Alembic manages schema migrations
All financial calculations happen in the backend

Example API endpoints:

GET    /accounts
POST   /accounts
PATCH  /accounts/{id}
DELETE /accounts/{id}

GET    /transactions
PATCH  /transactions/{id}

GET    /categories
POST   /categories
PATCH  /categories/{id}
DELETE /categories/{id}

The frontend doesn't need to know anything about SQLite.
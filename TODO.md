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

The initial countries of interest are Italy, Sweden, and China, with the architecture designed to be extensible.

2. Frontend and backend

We decided that the application should have two repositories:

matapan-backend
matapan-frontend
Backend

Responsible for everything involving financial data and business logic:

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
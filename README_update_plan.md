# README.md Update Plan

## Current State
README.md is 37 lines, describing a JSON-based system. The TODO.md specifies a more mature architecture using SQLite, Python/FastAPI, React/TypeScript, and Docker.

## Discrepancies to Fix

| README says | TODO.md says |
|-------------|--------------|
| JSON database | SQLite (matapan.db) |
| Single app | Frontend + Backend split |
| No mention of FX | Daily FX rates for multi-currency |
| No AI mention | Ollama integration |
| No deployment info | Docker/home-server |

## Proposed README Structure

```markdown
# Matapan: Financial Analyst for Expats

## One-line description
Local-first financial analysis application for expats with multi-currency support.

## What is Matapan? (expand on the coin metaphor)

## Core Features
- Multi-currency transaction tracking
- Bank statement parsing (Revolut, IB, SEB, etc.)
- Net worth and cash flow calculation
- Daily FX rate conversion
- AI-assisted transaction categorization (optional Ollama)
- Local-first: your data stays yours

## Architecture

### System Overview
                    PC / Phone / Tablet
                           │
                           ▼
                  ┌─────────────────┐
                  │    Frontend     │
                  │  React/TS       │
                  └────────┬────────┘
                           │ API
                           ▼
                  ┌─────────────────┐
                  │     Backend     │
                  │  Python/FastAPI │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │     SQLite      │
                  │  matapan.db     │
                  └─────────────────┘

### Backend Structure
matapan-backend/
├── app/
│   ├── api/          # REST endpoints
│   ├── core/         # Business logic
│   ├── database/     # SQLAlchemy + migrations
│   ├── parsers/      # Bank-specific parsers
│   ├── services/     # FX, AI, etc.
│   └── ai/           # Ollama integration
├── migrations/
└── tests/

### Supported Parsers
- Revolut (Excel export)
- Interactive Brokers
- Intesa Sanpaolo
- SEB (Skandinaviska Enskilda Banken)
- China Construction Bank
- Alipay
- WeChat

## Tech Stack
- Backend: Python, FastAPI, SQLAlchemy/SQLModel
- Database: SQLite
- AI: Ollama (local, optional)
- FX Rates: FreeCurrencyAPI
- Deployment: Docker/Docker Compose

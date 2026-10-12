"""Thin HTTP API for the first local backend test."""

import hashlib
import re
import secrets
from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import (
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.trustedhost import TrustedHostMiddleware

from matapan import __version__, imports
from matapan.db import database_url, make_engine, require_current_schema
from matapan.importers.revolut import MAX_FILE_BYTES, StatementError
from matapan.models import Account, AccountBalance, ImportRow, Transaction
from matapan.reports import account_report


def calendar_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Send a calendar date in YYYY-MM-DD format")
    return date.fromisoformat(value)


CalendarDate = Annotated[date, BeforeValidator(calendar_date)]


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AccountCreate(RequestModel):
    name: str = Field(min_length=1, max_length=120)
    institution: str | None = Field(default=None, min_length=1, max_length=120)
    currency_code: str = Field(pattern=r"^[A-Z]{3}$")
    revolut_product: Literal["Current", "Savings"] | None = None

    @field_validator("currency_code", mode="before")
    @classmethod
    def normalize_currency(cls, value):
        return value.strip().upper() if isinstance(value, str) else value


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    institution: str | None
    currency_code: str
    revolut_product: Literal["Current", "Savings"] | None
    created_at: datetime


class BalanceCreate(RequestModel):
    currency_code: str = Field(pattern=r"^[A-Z]{3}$")
    as_of_date: CalendarDate
    amount: Decimal = Field(max_digits=28, decimal_places=8, allow_inf_nan=False)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("currency_code", mode="before")
    @classmethod
    def normalize_currency(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("amount", mode="before", json_schema_input_type=str)
    @classmethod
    def exact_amount(cls, value):
        if not isinstance(value, str) or not re.fullmatch(
            r"-?(0|[1-9][0-9]*)(\.[0-9]{1,8})?", value
        ):
            raise ValueError("Send amount as a decimal string, for example '1234.50'")
        return Decimal(value)


class BalanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    currency_code: str
    as_of_date: date
    amount: Decimal
    source: Literal["manual", "revolut"]
    status: Literal["user_confirmed", "source_reported"]
    source_timestamp: str | None
    note: str | None
    recorded_at: datetime


class AccountReport(BaseModel):
    account_id: UUID
    currency_code: str
    as_of_date: date
    scope: Literal["account_cash"]
    status: Literal["partial", "unavailable"]
    amount: Decimal | None
    balance_as_of_date: date | None
    balance_status: Literal["user_confirmed", "source_reported", "missing", "conflicted"]
    source: Literal["manual", "revolut"] | None
    source_timestamp: str | None
    observation_ids: list[UUID]
    carried_forward: bool
    issues: list[str]


class HealthRead(BaseModel):
    status: Literal["ok"]
    database: Literal["ok"]
    version: str


class RowDecision(RequestModel):
    row_id: UUID
    action: Literal["keep_separate", "link_duplicate", "skip"]
    transaction_id: UUID | None = None

    @model_validator(mode="after")
    def require_target(self):
        if (self.action == "link_duplicate") != (self.transaction_id is not None):
            raise ValueError("transaction_id is required only for link_duplicate")
        return self


class ImportCommit(RequestModel):
    decisions: list[RowDecision] = Field(default_factory=list, max_length=10_000)
    include_balance: bool = True


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    currency_code: str
    product: str
    transaction_type: str
    posted_at: datetime
    started_at: datetime
    amount: Decimal
    source_amount: Decimal
    fee: Decimal
    source_description: str
    import_row_ids: list[UUID] = Field(default_factory=list)


SESSION_COOKIE = "matapan_import_session"


def import_owner(request: Request, response: Response | None = None) -> str:
    token = request.cookies.get(SESSION_COOKIE, "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        if response is None:
            raise imports.ImportProblem(404, "Import preview not found in this browser session")
        token = secrets.token_urlsafe(32)
        response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="strict", max_age=86_400)
    return hashlib.sha256(token.encode()).hexdigest()


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.sessions() as session:
        yield session


DatabaseSession = Annotated[Session, Depends(get_session)]
PageLimit = Annotated[int, Query(ge=1, le=100)]
PageOffset = Annotated[int, Query(ge=0)]


def get_account(session: Session, account_id: UUID) -> Account:
    account = session.get(Account, str(account_id))
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


def create_app(url: str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        engine = make_engine(url or database_url())
        try:
            require_current_schema(engine)
            application.state.sessions = sessionmaker(engine, expire_on_commit=False)
            yield
        finally:
            engine.dispose()

    application = FastAPI(
        title="Matapan API",
        version=__version__,
        description=(
            "Local backend test: accounts and manually confirmed dated cash balances. "
            "Revolut CSV imports require a preview and explicit confirmation. "
            "Send monetary amounts as decimal strings."
        ),
        lifespan=lifespan,
    )
    application.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]"]
    )

    @application.exception_handler(imports.ImportProblem)
    async def handle_import_problem(request: Request, error: imports.ImportProblem):
        return JSONResponse(status_code=error.status_code, content={"detail": error.detail})

    @application.exception_handler(StatementError)
    async def handle_statement_error(request: Request, error: StatementError):
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @application.get("/health", response_model=HealthRead, tags=["Health"])
    def health(session: DatabaseSession):
        try:
            session.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            raise HTTPException(status_code=503, detail="Database unavailable") from error
        return {"status": "ok", "database": "ok", "version": __version__}

    @application.post(
        "/api/v1/accounts",
        response_model=AccountRead,
        status_code=status.HTTP_201_CREATED,
        tags=["Accounts"],
    )
    def create_account(payload: AccountCreate, session: DatabaseSession):
        account = Account(**payload.model_dump())
        session.add(account)
        session.commit()
        return account

    @application.get("/api/v1/accounts", response_model=list[AccountRead], tags=["Accounts"])
    def list_accounts(session: DatabaseSession, limit: PageLimit = 100, offset: PageOffset = 0):
        return session.scalars(
            select(Account).order_by(Account.created_at, Account.id).limit(limit).offset(offset)
        ).all()

    @application.get("/api/v1/accounts/{account_id}", response_model=AccountRead, tags=["Accounts"])
    def read_account(account_id: UUID, session: DatabaseSession):
        return get_account(session, account_id)

    @application.delete(
        "/api/v1/accounts/{account_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["Accounts"],
        summary="Delete an empty account",
        description=(
            "Permanently delete an account only when it has no balances, transactions, "
            "or import history (including cancelled or expired previews). "
            "Linked records are preserved and block deletion."
        ),
        responses={
            404: {"description": "Account not found"},
            409: {"description": "Account has linked records and cannot be deleted"},
        },
    )
    def delete_account(account_id: UUID, session: DatabaseSession):
        account = get_account(session, account_id)
        session.delete(account)
        try:
            # Database RESTRICT constraints protect linked data, including concurrent writes.
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(
                status_code=409,
                detail=(
                    "Account has balances, transactions, or import history and cannot be deleted."
                ),
            ) from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.post(
        "/api/v1/accounts/{account_id}/cash-balances",
        response_model=BalanceRead,
        status_code=status.HTTP_201_CREATED,
        tags=["Balances"],
        summary="Confirm a manual cash balance for its stated date",
    )
    def create_balance(account_id: UUID, payload: BalanceCreate, session: DatabaseSession):
        account = get_account(session, account_id)
        if payload.currency_code != account.currency_code:
            raise HTTPException(
                status_code=422, detail="Balance currency must match account currency"
            )
        observation = AccountBalance(account_id=account.id, **payload.model_dump())
        session.add(observation)
        session.commit()
        return observation

    @application.get(
        "/api/v1/accounts/{account_id}/cash-balances",
        response_model=list[BalanceRead],
        tags=["Balances"],
    )
    def list_balances(
        account_id: UUID, session: DatabaseSession, limit: PageLimit = 100, offset: PageOffset = 0
    ):
        get_account(session, account_id)
        return session.scalars(
            select(AccountBalance)
            .where(AccountBalance.account_id == str(account_id))
            .order_by(
                AccountBalance.as_of_date.desc(), AccountBalance.recorded_at, AccountBalance.id
            )
            .limit(limit)
            .offset(offset)
        ).all()

    @application.get(
        "/api/v1/accounts/{account_id}/report", response_model=AccountReport, tags=["Reports"]
    )
    def read_report(account_id: UUID, as_of: CalendarDate, session: DatabaseSession):
        return account_report(session, get_account(session, account_id), as_of)

    @application.post("/api/v1/imports/preview", tags=["Imports"])
    def preview_import(
        account_id: Annotated[UUID, Form()],
        file: UploadFile,
        request: Request,
        response: Response,
        session: DatabaseSession,
    ):
        content = file.file.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="Statement exceeds the 10 MiB file limit")
        return imports.create_preview(
            session, str(account_id), content, import_owner(request, response)
        )

    @application.get("/api/v1/imports/{preview_id}", tags=["Imports"])
    def read_import(preview_id: UUID, request: Request, session: DatabaseSession):
        return imports.read_preview(session, str(preview_id), import_owner(request))

    @application.post("/api/v1/imports/{preview_id}/commit", tags=["Imports"])
    def commit_import(
        preview_id: UUID,
        payload: ImportCommit,
        request: Request,
        session: DatabaseSession,
    ):
        return imports.commit_preview(
            session,
            str(preview_id),
            import_owner(request),
            [decision.model_dump() for decision in payload.decisions],
            payload.include_balance,
        )

    @application.post("/api/v1/imports/{preview_id}/cancel", tags=["Imports"])
    def cancel_import(preview_id: UUID, request: Request, session: DatabaseSession):
        return imports.cancel_preview(session, str(preview_id), import_owner(request))

    @application.get(
        "/api/v1/accounts/{account_id}/transactions",
        response_model=list[TransactionRead],
        tags=["Transactions"],
    )
    def list_transactions(
        account_id: UUID,
        session: DatabaseSession,
        limit: PageLimit = 100,
        offset: PageOffset = 0,
    ):
        get_account(session, account_id)
        transactions = session.scalars(
            select(Transaction)
            .where(Transaction.account_id == str(account_id))
            .order_by(Transaction.posted_at.desc(), Transaction.id)
            .limit(limit)
            .offset(offset)
        ).all()
        provenance = {}
        if transactions:
            for row_id, transaction_id in session.execute(
                select(ImportRow.id, ImportRow.transaction_id).where(
                    ImportRow.transaction_id.in_([item.id for item in transactions])
                )
            ):
                provenance.setdefault(transaction_id, []).append(row_id)
        result = []
        for transaction in transactions:
            item = TransactionRead.model_validate(transaction)
            item.import_row_ids = [UUID(row_id) for row_id in provenance.get(transaction.id, [])]
            result.append(item)
        return result

    return application


app = create_app()

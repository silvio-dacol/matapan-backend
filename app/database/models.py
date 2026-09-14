"""Database models for Matapan."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class AccountType(str, Enum):
    """Types of financial accounts."""

    CHECKING = "checking"
    SAVINGS = "savings"
    INVESTMENT = "investment"
    CREDIT = "credit"
    CASH = "cash"
    OTHER = "other"


class TransactionType(str, Enum):
    """Types of transactions."""

    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    FEE = "fee"
    REFUND = "refund"


class Currency(SQLModel, table=True):
    """Currency model."""

    __tablename__ = "currencies"

    code: str = Field(primary_key, max_length=3, description="ISO 4217 currency code")
    name: str = Field(max_length=100, description="Currency name")
    symbol: Optional[str] = Field(default=None, max_length=10, description="Currency symbol")
    decimal_places: int = Field(default=2, description="Number of decimal places")

    # Relationships
    accounts: list["Account"] = Relationship(back_populates="currency")
    transactions: list["Transaction"] = Relationship(back_populates="currency")
    fx_rates_from: list["FxRate"] = Relationship(
        back_populates="from_currency", sa_relationship_kwargs={"foreign_keys": "FxRate.from_currency_code"}
    )
    fx_rates_to: list["FxRate"] = Relationship(
        back_populates="to_currency", sa_relationship_kwargs={"foreign_keys": "FxRate.to_currency_code"}
    )


class FxRate(SQLModel, table=True):
    """Daily foreign exchange rates."""

    __tablename__ = "fx_rates"

    id: Optional[int] = Field(default=None, primary_key)
    date: date = Field(index=True, description="Rate date")
    from_currency_code: str = Field(
        max_length=3,
        foreign_key="currencies.code",
        index=True,
        description="Source currency",
    )
    to_currency_code: str = Field(
        max_length=3,
        foreign_key="currencies.code",
        index=True,
        description="Target currency",
    )
    rate: Decimal = Field(decimal_places=10, description="Exchange rate")
    source: Optional[str] = Field(default=None, max_length=100, description="Rate source")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    from_currency: Optional[Currency] = Relationship(
        back_populates="fx_rates_from",
        sa_relationship_kwargs={"foreign_keys": [from_currency_code]},
    )
    to_currency: Optional[Currency] = Relationship(
        back_populates="fx_rates_to",
        sa_relationship_kwargs={"foreign_keys": [to_currency_code]},
    )

    class Config:
        """SQLModel config."""

        # Ensure unique rate per currency pair per day
        # This would be enforced at DB level via unique_constraint


class Institution(SQLModel, table=True):
    """Financial institution (bank, broker, etc.)."""

    __tablename__ = "institutions"

    id: Optional[int] = Field(default=None, primary_key)
    name: str = Field(max_length=200, description="Institution name")
    country: Optional[str] = Field(default=None, max_length=100, description="Country")
    parser_name: Optional[str] = Field(
        default=None, max_length=100, description="Parser identifier for this institution"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    accounts: list["Account"] = Relationship(back_populates="institution")


class Account(SQLModel, table=True):
    """Financial account."""

    __tablename__ = "accounts"

    id: Optional[int] = Field(default=None, primary_key)
    name: str = Field(max_length=200, description="Account name")
    account_type: AccountType = Field(description="Type of account")
    currency_code: str = Field(
        max_length=3,
        foreign_key="currencies.code",
        description="Account currency",
    )
    institution_id: Optional[int] = Field(
        default=None, foreign_key="institutions.id", description="Institution ID"
    )
    account_number: Optional[str] = Field(
        default=None, max_length=100, description="Account number or IBAN"
    )
    is_active: bool = Field(default=True, description="Whether account is active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    currency: Optional[Currency] = Relationship(back_populates="accounts")
    institution: Optional[Institution] = Relationship(back_populates="accounts")
    transactions: list["Transaction"] = Relationship(back_populates="account")
    balances: list["AccountBalance"] = Relationship(back_populates="account")


class AccountBalance(SQLModel, table=True):
    """Account balance at a specific date."""

    __tablename__ = "account_balances"

    id: Optional[int] = Field(default=None, primary_key)
    account_id: int = Field(foreign_key="accounts.id", index=True, description="Account ID")
    date: date = Field(index=True, description="Balance date")
    balance: Decimal = Field(decimal_places=2, description="Account balance")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    account: Optional[Account] = Relationship(back_populates="balances")


class Category(SQLModel, table=True):
    """Transaction category."""

    __tablename__ = "categories"

    id: Optional[int] = Field(default=None, primary_key)
    name: str = Field(max_length=100, description="Category name")
    parent_id: Optional[int] = Field(
        default=None, foreign_key="categories.id", description="Parent category ID"
    )
    description: Optional[str] = Field(default=None, description="Category description")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    transactions: list["Transaction"] = Relationship(back_populates="category")


class Transaction(SQLModel, table=True):
    """Financial transaction."""

    __tablename__ = "transactions"

    id: Optional[int] = Field(default=None, primary_key)
    account_id: int = Field(foreign_key="accounts.id", index=True, description="Account ID")
    date: date = Field(index=True, description="Transaction date")
    amount: Decimal = Field(decimal_places=2, description="Transaction amount in original currency")
    currency_code: str = Field(
        max_length=3,
        foreign_key="currencies.code",
        description="Original currency",
    )
    transaction_type: TransactionType = Field(description="Type of transaction")
    description: Optional[str] = Field(default=None, max_length=500, description="Transaction description")
    original_description: Optional[str] = Field(
        default=None, max_length=500, description="Original description from bank"
    )
    category_id: Optional[int] = Field(
        default=None, foreign_key="categories.id", index=True, description="Category ID"
    )
    # Amount converted to reporting currency (e.g., CHF)
    amount_in_reporting_currency: Optional[Decimal] = Field(
        default=None, decimal_places=2, description="Amount in reporting currency"
    )
    # FX rate used if conversion was done
    fx_rate_used: Optional[Decimal] = Field(
        default=None, decimal_places=10, description="FX rate used for conversion"
    )
    # For investments
    ticker: Optional[str] = Field(default=None, max_length=20, description="Security ticker")
    quantity: Optional[Decimal] = Field(default=None, decimal_places=6, description="Quantity traded")
    price: Optional[Decimal] = Field(
        default=None, decimal_places=6, description="Price per unit"
    )
    # Metadata
    reference_id: Optional[str] = Field(
        default=None, max_length=200, description="Bank's transaction reference"
    )
    is_reconciled: bool = Field(default=False, description="Whether transaction is reconciled")
    parser_used: Optional[str] = Field(
        default=None, max_length=100, description="Parser that processed this transaction"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    account: Optional[Account] = Relationship(back_populates="transactions")
    currency: Optional[Currency] = Relationship(back_populates="transactions")
    category: Optional[Category] = Relationship(back_populates="transactions")
    tags: list["TransactionTag"] = Relationship(back_populates="transaction")


class Tag(SQLModel, table=True):
    """Tag for transactions."""

    __tablename__ = "tags"

    id: Optional[int] = Field(default=None, primary_key)
    name: str = Field(max_length=50, unique=True, description="Tag name")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    transactions: list["TransactionTag"] = Relationship(back_populates="tag")


class TransactionTag(SQLModel, table=True):
    """Many-to-many relationship between transactions and tags."""

    __tablename__ = "transaction_tags"

    transaction_id: int = Field(foreign_key="transactions.id", primary_key=True)
    tag_id: int = Field(foreign_key="tags.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    transaction: Optional[Transaction] = Relationship(back_populates="tags")
    tag: Optional[Tag] = Relationship(back_populates="transactions")


class Asset(SQLModel, table=True):
    """Real asset (property, car, etc.)."""

    __tablename__ = "assets"

    id: Optional[int] = Field(default=None, primary_key)
    name: str = Field(max_length=200, description="Asset name")
    asset_type: str = Field(max_length=100, description="Type of asset")
    currency_code: str = Field(max_length=3, foreign_key="currencies.code")
    current_value: Decimal = Field(decimal_places=2, description="Current value")
    purchase_price: Optional[Decimal] = Field(
        default=None, decimal_places=2, description="Purchase price"
    )
    purchase_date: Optional[date] = Field(default=None, description="Purchase date")
    notes: Optional[str] = Field(default=None, description="Notes about the asset")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Liability(SQLModel, table=True):
    """Liability (loan, mortgage, etc.)."""

    __tablename__ = "liabilities"

    id: Optional[int] = Field(default=None, primary_key)
    name: str = Field(max_length=200, description="Liability name")
    liability_type: str = Field(max_length=100, description="Type of liability")
    currency_code: str = Field(max_length=3, foreign_key="currencies.code")
    current_value: Decimal = Field(decimal_places=2, description="Current amount owed")
    original_value: Optional[Decimal] = Field(
        default=None, decimal_places=2, description="Original loan amount"
    )
    interest_rate: Optional[Decimal] = Field(
        default=None, decimal_places=4, description="Interest rate"
    )
    start_date: Optional[date] = Field(default=None, description="Start date")
    end_date: Optional[date] = Field(default=None, description="End date")
    notes: Optional[str] = Field(default=None, description="Notes about the liability")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ParserMetadata(SQLModel, table=True):
    """Metadata about parsed files."""

    __tablename__ = "parser_metadata"

    id: Optional[int] = Field(default=None, primary_key)
    parser_name: str = Field(max_length=100, index=True, description="Parser identifier")
    file_name: str = Field(max_length=500, description="Original file name")
    file_hash: Optional[str] = Field(
        default=None, max_length=64, description="SHA256 hash of file"
    )
    parse_date: datetime = Field(default_factory=datetime.utcnow, description="When file was parsed")
    records_imported: int = Field(default=0, description="Number of records imported")
    account_id: Optional[int] = Field(
        default=None, foreign_key="accounts.id", description="Account records were imported to"
    )

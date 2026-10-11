"""Create accounts and manual cash balance observations.

Revision ID: 0001_account_balances
Revises: None
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_account_balances"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("institution", sa.String(120), nullable=True),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("length(name) BETWEEN 1 AND 120", name="ck_account_name"),
        sa.CheckConstraint("currency_code GLOB '[A-Z][A-Z][A-Z]'", name="ck_account_currency"),
    )
    op.create_table(
        "account_balances",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.String(64), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("currency_code GLOB '[A-Z][A-Z][A-Z]'", name="ck_balance_currency"),
        sa.CheckConstraint("length(amount) BETWEEN 1 AND 64", name="ck_balance_amount"),
        sa.CheckConstraint("source = 'manual'", name="ck_balance_source"),
        sa.CheckConstraint("status = 'user_confirmed'", name="ck_balance_status"),
    )
    op.create_index(
        "ix_balance_account_currency_date",
        "account_balances",
        ["account_id", "currency_code", "as_of_date"],
    )


def downgrade() -> None:
    # Do not offer a schema-reset shortcut that destroys financial evidence.
    raise RuntimeError("This migration cannot be downgraded: preserve the financial database.")

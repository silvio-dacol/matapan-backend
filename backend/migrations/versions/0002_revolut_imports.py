"""Add reviewed Revolut imports and their canonical records without resetting data."""

import sqlalchemy as sa
from alembic import op

revision = "0002_revolut_imports"
down_revision = "0001_account_balances"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("revolut_product", sa.String(20), nullable=True))
    with op.batch_alter_table("account_balances") as batch:
        batch.add_column(sa.Column("source_timestamp", sa.String(19), nullable=True))
        batch.drop_constraint("ck_balance_source", type_="check")
        batch.drop_constraint("ck_balance_status", type_="check")
        batch.create_check_constraint("ck_balance_source", "source IN ('manual', 'revolut')")
        batch.create_check_constraint(
            "ck_balance_status", "status IN ('user_confirmed', 'source_reported')"
        )
        batch.create_unique_constraint(
            "uq_balance_source_checkpoint",
            ["account_id", "currency_code", "source", "source_timestamp"],
        )
    op.create_table(
        "import_batches",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("product", sa.String(20), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("parser_id", sa.String(40), nullable=False),
        sa.Column("parser_version", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("owner_hash", sa.String(64), nullable=False),
        sa.Column("observed_start", sa.DateTime(), nullable=True),
        sa.Column("observed_end", sa.DateTime(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("committed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "account_id", "file_hash", "parser_id", "parser_version", name="uq_import_file_context"
        ),
        sa.CheckConstraint(
            "status IN ('preview', 'committed', 'cancelled')", name="ck_import_status"
        ),
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("product", sa.String(20), nullable=False),
        sa.Column("transaction_type", sa.String(64), nullable=False),
        sa.Column("posted_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("amount", sa.String(64), nullable=False),
        sa.Column("source_amount", sa.String(64), nullable=False),
        sa.Column("fee", sa.String(64), nullable=False),
        sa.Column("source_description", sa.String(500), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_transaction_account_date", "transactions", ["account_id", "posted_at"])
    op.create_index(
        "ix_transaction_match", "transactions", ["account_id", "currency_code", "fingerprint"]
    )
    op.create_table(
        "import_rows",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("batch_id", sa.String(36), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("classification", sa.String(24), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("product", sa.String(20), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("source_state", sa.String(20), nullable=False),
        sa.Column("transaction_type", sa.String(64), nullable=False),
        sa.Column("source_description", sa.String(500), nullable=False),
        sa.Column("posted_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("amount", sa.String(64), nullable=True),
        sa.Column("source_amount", sa.String(64), nullable=True),
        sa.Column("fee", sa.String(64), nullable=True),
        sa.Column("balance", sa.String(64), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=True),
        sa.Column("decision", sa.String(24), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("transaction_id", sa.String(36), nullable=True),
        sa.Column("balance_id", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["import_batches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"]),
        sa.ForeignKeyConstraint(["balance_id"], ["account_balances.id"]),
        sa.UniqueConstraint("batch_id", "row_number", name="uq_import_row_number"),
    )


def downgrade() -> None:
    raise RuntimeError(
        "Preserve imported financial evidence; this migration has no destructive downgrade."
    )

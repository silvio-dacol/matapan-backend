"""Add timed checkpoints and audited adjustments without changing existing evidence."""

import sqlalchemy as sa
from alembic import op

revision = "0003_reconciliation"
down_revision = "0002_revolut_imports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("statement_timezone", sa.String(100), nullable=True))
    op.add_column("account_balances", sa.Column("effective_at", sa.DateTime(), nullable=True))
    op.add_column("account_balances", sa.Column("effective_offset", sa.String(6), nullable=True))
    op.create_table(
        "reconciliations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("opening_balance_id", sa.String(36), nullable=False),
        sa.Column("closing_balance_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["opening_balance_id"], ["account_balances.id"]),
        sa.ForeignKeyConstraint(["closing_balance_id"], ["account_balances.id"]),
        sa.UniqueConstraint(
            "opening_balance_id", "closing_balance_id", name="uq_reconciliation_pair"
        ),
    )
    op.create_table(
        "reconciliation_adjustments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("reconciliation_id", sa.String(36), nullable=False),
        sa.Column("amount", sa.String(64), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("actor", sa.String(40), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=False),
        sa.Column("replaces_id", sa.String(36), nullable=True),
        sa.Column("evidence_signature", sa.String(64), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["reconciliation_id"], ["reconciliations.id"]),
        sa.ForeignKeyConstraint(["replaces_id"], ["reconciliation_adjustments.id"]),
        sa.CheckConstraint(
            "state IN ('active', 'superseded', 'reversed')", name="ck_adjustment_state"
        ),
    )
    op.create_index(
        "uq_active_reconciliation_adjustment",
        "reconciliation_adjustments",
        ["reconciliation_id"],
        unique=True,
        sqlite_where=sa.text("state = 'active'"),
    )


def downgrade() -> None:
    raise RuntimeError("Preserve checkpoints and adjustment approvals; no destructive downgrade.")

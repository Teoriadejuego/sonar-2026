"""add emails interest capture table

Revision ID: 20260502_11
Revises: 20260502_10
Create Date: 2026-05-02 20:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260502_11"
down_revision = "20260502_10"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(
        index["name"] == index_name
        for index in _inspector().get_indexes(table_name)
    )


def _has_unique_constraint(table_name: str, constraint_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(
        constraint["name"] == constraint_name
        for constraint in _inspector().get_unique_constraints(table_name)
    )


def upgrade() -> None:
    if not _has_table("emails_interest"):
        op.create_table(
            "emails_interest",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column(
                "source",
                sa.String(),
                nullable=False,
                server_default="panic_screen",
            ),
        )
    if not _has_unique_constraint(
        "emails_interest",
        "uq_emails_interest_email_source",
    ):
        op.create_unique_constraint(
            "uq_emails_interest_email_source",
            "emails_interest",
            ["email", "source"],
        )
    if not _has_index("emails_interest", "ix_emails_interest_email"):
        op.create_index(
            "ix_emails_interest_email",
            "emails_interest",
            ["email"],
            unique=False,
        )
    if not _has_index("emails_interest", "ix_emails_interest_timestamp"):
        op.create_index(
            "ix_emails_interest_timestamp",
            "emails_interest",
            ["timestamp"],
            unique=False,
        )
    if not _has_index("emails_interest", "ix_emails_interest_source"):
        op.create_index(
            "ix_emails_interest_source",
            "emails_interest",
            ["source"],
            unique=False,
        )


def downgrade() -> None:
    if _has_index("emails_interest", "ix_emails_interest_source"):
        op.drop_index("ix_emails_interest_source", table_name="emails_interest")
    if _has_index("emails_interest", "ix_emails_interest_timestamp"):
        op.drop_index("ix_emails_interest_timestamp", table_name="emails_interest")
    if _has_index("emails_interest", "ix_emails_interest_email"):
        op.drop_index("ix_emails_interest_email", table_name="emails_interest")
    if _has_unique_constraint(
        "emails_interest",
        "uq_emails_interest_email_source",
    ):
        op.drop_constraint(
            "uq_emails_interest_email_source",
            "emails_interest",
            type_="unique",
        )
    if _has_table("emails_interest"):
        op.drop_table("emails_interest")

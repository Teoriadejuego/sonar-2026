"""recover missing tables for legacy deployments

Revision ID: 20260410_05
Revises: 20260410_04
Create Date: 2026-04-10 23:55:00
"""

from alembic import op
from sqlmodel import SQLModel

from models import *  # noqa: F401,F403


revision = "20260410_05"
down_revision = "20260410_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    SQLModel.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    pass

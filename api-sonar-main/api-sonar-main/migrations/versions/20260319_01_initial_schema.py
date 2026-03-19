"""initial schema

Revision ID: 20260319_01
Revises:
Create Date: 2026-03-19 00:00:00
"""

from alembic import op
from sqlmodel import SQLModel

from models import *  # noqa: F401,F403


revision = "20260319_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    SQLModel.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    SQLModel.metadata.drop_all(bind=bind)

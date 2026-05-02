"""add referral tracking tables

Revision ID: 20260502_08
Revises: 20260502_07
Create Date: 2026-05-02 17:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260502_08"
down_revision = "20260502_07"
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


def upgrade() -> None:
    if not _has_table("referral_links"):
        op.create_table(
            "referral_links",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("inviter_session_id", sa.String(), nullable=False),
            sa.Column("inviter_user_id", sa.String(), nullable=True),
            sa.Column("inviter_referral_code", sa.String(), nullable=False),
            sa.Column(
                "channel",
                sa.String(),
                nullable=False,
                server_default="whatsapp",
            ),
            sa.Column("traffic_source", sa.String(), nullable=True),
            sa.Column("traffic_medium", sa.String(), nullable=True),
            sa.Column("campaign_code", sa.String(), nullable=True),
            sa.Column(
                "target_path",
                sa.Text(),
                nullable=False,
                server_default="/",
            ),
            sa.Column(
                "click_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "conversion_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("first_clicked_at", sa.DateTime(), nullable=True),
            sa.Column("last_clicked_at", sa.DateTime(), nullable=True),
            sa.Column("first_converted_at", sa.DateTime(), nullable=True),
            sa.Column("last_converted_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["inviter_session_id"], ["sessions.id"]),
            sa.ForeignKeyConstraint(["inviter_user_id"], ["users.id"]),
        )
    if not _has_index("referral_links", "ix_referral_links_inviter_session_id"):
        op.create_index(
            "ix_referral_links_inviter_session_id",
            "referral_links",
            ["inviter_session_id"],
            unique=False,
        )
    if not _has_index("referral_links", "ix_referral_links_inviter_user_id"):
        op.create_index(
            "ix_referral_links_inviter_user_id",
            "referral_links",
            ["inviter_user_id"],
            unique=False,
        )
    if not _has_index("referral_links", "ix_referral_links_inviter_referral_code"):
        op.create_index(
            "ix_referral_links_inviter_referral_code",
            "referral_links",
            ["inviter_referral_code"],
            unique=False,
        )
    if not _has_index("referral_links", "ix_referral_links_channel"):
        op.create_index(
            "ix_referral_links_channel",
            "referral_links",
            ["channel"],
            unique=False,
        )
    if not _has_index("referral_links", "ix_referral_links_traffic_source"):
        op.create_index(
            "ix_referral_links_traffic_source",
            "referral_links",
            ["traffic_source"],
            unique=False,
        )
    if not _has_index("referral_links", "ix_referral_links_traffic_medium"):
        op.create_index(
            "ix_referral_links_traffic_medium",
            "referral_links",
            ["traffic_medium"],
            unique=False,
        )
    if not _has_index("referral_links", "ix_referral_links_campaign_code"):
        op.create_index(
            "ix_referral_links_campaign_code",
            "referral_links",
            ["campaign_code"],
            unique=False,
        )
    if not _has_index(
        "referral_links",
        "ix_referral_links_inviter_session_id_created_at",
    ):
        op.create_index(
            "ix_referral_links_inviter_session_id_created_at",
            "referral_links",
            ["inviter_session_id", "created_at"],
            unique=False,
        )
    if not _has_index("referral_links", "ix_referral_links_channel_created_at"):
        op.create_index(
            "ix_referral_links_channel_created_at",
            "referral_links",
            ["channel", "created_at"],
            unique=False,
        )

    if not _has_table("referral_clicks"):
        op.create_table(
            "referral_clicks",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("referral_link_id", sa.String(), nullable=False),
            sa.Column("inviter_session_id", sa.String(), nullable=True),
            sa.Column("session_id", sa.String(), nullable=True),
            sa.Column("request_host", sa.String(), nullable=True),
            sa.Column("request_path", sa.String(), nullable=False),
            sa.Column("query_string", sa.Text(), nullable=True),
            sa.Column("referer", sa.Text(), nullable=True),
            sa.Column("traffic_source", sa.String(), nullable=True),
            sa.Column("traffic_medium", sa.String(), nullable=True),
            sa.Column("request_user_agent", sa.Text(), nullable=True),
            sa.Column("ip_hash", sa.String(), nullable=True),
            sa.Column("user_agent_hash", sa.String(), nullable=True),
            sa.Column("redirect_status_code", sa.Integer(), nullable=True),
            sa.Column(
                "status",
                sa.String(),
                nullable=False,
                server_default="redirected",
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["referral_link_id"], ["referral_links.id"]),
            sa.ForeignKeyConstraint(["inviter_session_id"], ["sessions.id"]),
            sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        )
    if not _has_index("referral_clicks", "ix_referral_clicks_referral_link_id"):
        op.create_index(
            "ix_referral_clicks_referral_link_id",
            "referral_clicks",
            ["referral_link_id"],
            unique=False,
        )
    if not _has_index("referral_clicks", "ix_referral_clicks_inviter_session_id"):
        op.create_index(
            "ix_referral_clicks_inviter_session_id",
            "referral_clicks",
            ["inviter_session_id"],
            unique=False,
        )
    if not _has_index("referral_clicks", "ix_referral_clicks_session_id"):
        op.create_index(
            "ix_referral_clicks_session_id",
            "referral_clicks",
            ["session_id"],
            unique=False,
        )
    if not _has_index("referral_clicks", "ix_referral_clicks_request_host"):
        op.create_index(
            "ix_referral_clicks_request_host",
            "referral_clicks",
            ["request_host"],
            unique=False,
        )
    if not _has_index("referral_clicks", "ix_referral_clicks_traffic_source"):
        op.create_index(
            "ix_referral_clicks_traffic_source",
            "referral_clicks",
            ["traffic_source"],
            unique=False,
        )
    if not _has_index("referral_clicks", "ix_referral_clicks_traffic_medium"):
        op.create_index(
            "ix_referral_clicks_traffic_medium",
            "referral_clicks",
            ["traffic_medium"],
            unique=False,
        )
    if not _has_index("referral_clicks", "ix_referral_clicks_ip_hash"):
        op.create_index(
            "ix_referral_clicks_ip_hash",
            "referral_clicks",
            ["ip_hash"],
            unique=False,
        )
    if not _has_index("referral_clicks", "ix_referral_clicks_user_agent_hash"):
        op.create_index(
            "ix_referral_clicks_user_agent_hash",
            "referral_clicks",
            ["user_agent_hash"],
            unique=False,
        )
    if not _has_index("referral_clicks", "ix_referral_clicks_status"):
        op.create_index(
            "ix_referral_clicks_status",
            "referral_clicks",
            ["status"],
            unique=False,
        )
    if not _has_index(
        "referral_clicks",
        "ix_referral_clicks_referral_link_id_created_at",
    ):
        op.create_index(
            "ix_referral_clicks_referral_link_id_created_at",
            "referral_clicks",
            ["referral_link_id", "created_at"],
            unique=False,
        )
    if not _has_index(
        "referral_clicks",
        "ix_referral_clicks_traffic_source_created_at",
    ):
        op.create_index(
            "ix_referral_clicks_traffic_source_created_at",
            "referral_clicks",
            ["traffic_source", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    if _has_index(
        "referral_clicks",
        "ix_referral_clicks_traffic_source_created_at",
    ):
        op.drop_index(
            "ix_referral_clicks_traffic_source_created_at",
            table_name="referral_clicks",
        )
    if _has_index(
        "referral_clicks",
        "ix_referral_clicks_referral_link_id_created_at",
    ):
        op.drop_index(
            "ix_referral_clicks_referral_link_id_created_at",
            table_name="referral_clicks",
        )
    if _has_index("referral_clicks", "ix_referral_clicks_status"):
        op.drop_index("ix_referral_clicks_status", table_name="referral_clicks")
    if _has_index("referral_clicks", "ix_referral_clicks_user_agent_hash"):
        op.drop_index(
            "ix_referral_clicks_user_agent_hash",
            table_name="referral_clicks",
        )
    if _has_index("referral_clicks", "ix_referral_clicks_ip_hash"):
        op.drop_index("ix_referral_clicks_ip_hash", table_name="referral_clicks")
    if _has_index("referral_clicks", "ix_referral_clicks_traffic_medium"):
        op.drop_index(
            "ix_referral_clicks_traffic_medium",
            table_name="referral_clicks",
        )
    if _has_index("referral_clicks", "ix_referral_clicks_traffic_source"):
        op.drop_index(
            "ix_referral_clicks_traffic_source",
            table_name="referral_clicks",
        )
    if _has_index("referral_clicks", "ix_referral_clicks_request_host"):
        op.drop_index(
            "ix_referral_clicks_request_host",
            table_name="referral_clicks",
        )
    if _has_index("referral_clicks", "ix_referral_clicks_session_id"):
        op.drop_index("ix_referral_clicks_session_id", table_name="referral_clicks")
    if _has_index("referral_clicks", "ix_referral_clicks_inviter_session_id"):
        op.drop_index(
            "ix_referral_clicks_inviter_session_id",
            table_name="referral_clicks",
        )
    if _has_index("referral_clicks", "ix_referral_clicks_referral_link_id"):
        op.drop_index(
            "ix_referral_clicks_referral_link_id",
            table_name="referral_clicks",
        )
    if _has_table("referral_clicks"):
        op.drop_table("referral_clicks")

    if _has_index("referral_links", "ix_referral_links_channel_created_at"):
        op.drop_index(
            "ix_referral_links_channel_created_at",
            table_name="referral_links",
        )
    if _has_index(
        "referral_links",
        "ix_referral_links_inviter_session_id_created_at",
    ):
        op.drop_index(
            "ix_referral_links_inviter_session_id_created_at",
            table_name="referral_links",
        )
    if _has_index("referral_links", "ix_referral_links_campaign_code"):
        op.drop_index("ix_referral_links_campaign_code", table_name="referral_links")
    if _has_index("referral_links", "ix_referral_links_traffic_medium"):
        op.drop_index("ix_referral_links_traffic_medium", table_name="referral_links")
    if _has_index("referral_links", "ix_referral_links_traffic_source"):
        op.drop_index("ix_referral_links_traffic_source", table_name="referral_links")
    if _has_index("referral_links", "ix_referral_links_channel"):
        op.drop_index("ix_referral_links_channel", table_name="referral_links")
    if _has_index("referral_links", "ix_referral_links_inviter_referral_code"):
        op.drop_index(
            "ix_referral_links_inviter_referral_code",
            table_name="referral_links",
        )
    if _has_index("referral_links", "ix_referral_links_inviter_user_id"):
        op.drop_index("ix_referral_links_inviter_user_id", table_name="referral_links")
    if _has_index("referral_links", "ix_referral_links_inviter_session_id"):
        op.drop_index(
            "ix_referral_links_inviter_session_id",
            table_name="referral_links",
        )
    if _has_table("referral_links"):
        op.drop_table("referral_links")

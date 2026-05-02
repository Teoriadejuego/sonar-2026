"""add gateway routing tables

Revision ID: 20260502_07
Revises: 20260502_06
Create Date: 2026-05-02 12:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260502_07"
down_revision = "20260502_06"
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
    if not _has_table("gateway_routes"):
        op.create_table(
            "gateway_routes",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("qr_code", sa.String(), nullable=False),
            sa.Column("zone_code", sa.String(), nullable=True),
            sa.Column("primary_target_url", sa.Text(), nullable=False),
            sa.Column("backup_target_url", sa.Text(), nullable=True),
            sa.Column(
                "active_target",
                sa.String(),
                nullable=False,
                server_default="primary",
            ),
            sa.Column(
                "enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("last_switched_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
    if not _has_index("gateway_routes", "ix_gateway_routes_qr_code"):
        op.create_index(
            "ix_gateway_routes_qr_code",
            "gateway_routes",
            ["qr_code"],
            unique=True,
        )
    if not _has_index("gateway_routes", "ix_gateway_routes_zone_code"):
        op.create_index(
            "ix_gateway_routes_zone_code",
            "gateway_routes",
            ["zone_code"],
            unique=False,
        )
    if not _has_index("gateway_routes", "ix_gateway_routes_active_target"):
        op.create_index(
            "ix_gateway_routes_active_target",
            "gateway_routes",
            ["active_target"],
            unique=False,
        )
    if not _has_index("gateway_routes", "ix_gateway_routes_enabled"):
        op.create_index(
            "ix_gateway_routes_enabled",
            "gateway_routes",
            ["enabled"],
            unique=False,
        )

    if not _has_table("gateway_access_logs"):
        op.create_table(
            "gateway_access_logs",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("route_id", sa.String(), nullable=True),
            sa.Column("qr_code", sa.String(), nullable=False),
            sa.Column("zone_code", sa.String(), nullable=True),
            sa.Column("session_id", sa.String(), nullable=True),
            sa.Column("gateway_visit_id", sa.String(), nullable=False),
            sa.Column("request_host", sa.String(), nullable=True),
            sa.Column("request_path", sa.String(), nullable=False),
            sa.Column("query_string", sa.Text(), nullable=True),
            sa.Column(
                "selected_target",
                sa.String(),
                nullable=False,
                server_default="primary",
            ),
            sa.Column("resolved_target_url", sa.Text(), nullable=True),
            sa.Column("redirect_status_code", sa.Integer(), nullable=True),
            sa.Column(
                "status",
                sa.String(),
                nullable=False,
                server_default="redirected",
            ),
            sa.Column("referer", sa.Text(), nullable=True),
            sa.Column("traffic_source", sa.String(), nullable=True),
            sa.Column("traffic_medium", sa.String(), nullable=True),
            sa.Column("request_user_agent", sa.Text(), nullable=True),
            sa.Column("ip_hash", sa.String(), nullable=True),
            sa.Column("user_agent_hash", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["route_id"], ["gateway_routes.id"]),
            sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        )
    if not _has_index("gateway_access_logs", "ix_gateway_access_logs_route_id"):
        op.create_index(
            "ix_gateway_access_logs_route_id",
            "gateway_access_logs",
            ["route_id"],
            unique=False,
        )
    if not _has_index("gateway_access_logs", "ix_gateway_access_logs_qr_code"):
        op.create_index(
            "ix_gateway_access_logs_qr_code",
            "gateway_access_logs",
            ["qr_code"],
            unique=False,
        )
    if not _has_index("gateway_access_logs", "ix_gateway_access_logs_zone_code"):
        op.create_index(
            "ix_gateway_access_logs_zone_code",
            "gateway_access_logs",
            ["zone_code"],
            unique=False,
        )
    if not _has_index("gateway_access_logs", "ix_gateway_access_logs_session_id"):
        op.create_index(
            "ix_gateway_access_logs_session_id",
            "gateway_access_logs",
            ["session_id"],
            unique=False,
        )
    if not _has_index("gateway_access_logs", "ix_gateway_access_logs_gateway_visit_id"):
        op.create_index(
            "ix_gateway_access_logs_gateway_visit_id",
            "gateway_access_logs",
            ["gateway_visit_id"],
            unique=True,
        )
    if not _has_index("gateway_access_logs", "ix_gateway_access_logs_request_host"):
        op.create_index(
            "ix_gateway_access_logs_request_host",
            "gateway_access_logs",
            ["request_host"],
            unique=False,
        )
    if not _has_index("gateway_access_logs", "ix_gateway_access_logs_selected_target"):
        op.create_index(
            "ix_gateway_access_logs_selected_target",
            "gateway_access_logs",
            ["selected_target"],
            unique=False,
        )
    if not _has_index("gateway_access_logs", "ix_gateway_access_logs_status"):
        op.create_index(
            "ix_gateway_access_logs_status",
            "gateway_access_logs",
            ["status"],
            unique=False,
        )
    if not _has_index("gateway_access_logs", "ix_gateway_access_logs_traffic_source"):
        op.create_index(
            "ix_gateway_access_logs_traffic_source",
            "gateway_access_logs",
            ["traffic_source"],
            unique=False,
        )
    if not _has_index("gateway_access_logs", "ix_gateway_access_logs_traffic_medium"):
        op.create_index(
            "ix_gateway_access_logs_traffic_medium",
            "gateway_access_logs",
            ["traffic_medium"],
            unique=False,
        )
    if not _has_index("gateway_access_logs", "ix_gateway_access_logs_ip_hash"):
        op.create_index(
            "ix_gateway_access_logs_ip_hash",
            "gateway_access_logs",
            ["ip_hash"],
            unique=False,
        )
    if not _has_index("gateway_access_logs", "ix_gateway_access_logs_user_agent_hash"):
        op.create_index(
            "ix_gateway_access_logs_user_agent_hash",
            "gateway_access_logs",
            ["user_agent_hash"],
            unique=False,
        )
    if not _has_index(
        "gateway_access_logs",
        "ix_gateway_access_logs_qr_code_created_at",
    ):
        op.create_index(
            "ix_gateway_access_logs_qr_code_created_at",
            "gateway_access_logs",
            ["qr_code", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    if _has_index("gateway_access_logs", "ix_gateway_access_logs_qr_code_created_at"):
        op.drop_index(
            "ix_gateway_access_logs_qr_code_created_at",
            table_name="gateway_access_logs",
        )
    if _has_index("gateway_access_logs", "ix_gateway_access_logs_traffic_medium"):
        op.drop_index(
            "ix_gateway_access_logs_traffic_medium",
            table_name="gateway_access_logs",
        )
    if _has_index("gateway_access_logs", "ix_gateway_access_logs_traffic_source"):
        op.drop_index(
            "ix_gateway_access_logs_traffic_source",
            table_name="gateway_access_logs",
        )
    if _has_index("gateway_access_logs", "ix_gateway_access_logs_user_agent_hash"):
        op.drop_index(
            "ix_gateway_access_logs_user_agent_hash",
            table_name="gateway_access_logs",
        )
    if _has_index("gateway_access_logs", "ix_gateway_access_logs_ip_hash"):
        op.drop_index(
            "ix_gateway_access_logs_ip_hash",
            table_name="gateway_access_logs",
        )
    if _has_index("gateway_access_logs", "ix_gateway_access_logs_status"):
        op.drop_index(
            "ix_gateway_access_logs_status",
            table_name="gateway_access_logs",
        )
    if _has_index("gateway_access_logs", "ix_gateway_access_logs_selected_target"):
        op.drop_index(
            "ix_gateway_access_logs_selected_target",
            table_name="gateway_access_logs",
        )
    if _has_index("gateway_access_logs", "ix_gateway_access_logs_request_host"):
        op.drop_index(
            "ix_gateway_access_logs_request_host",
            table_name="gateway_access_logs",
        )
    if _has_index("gateway_access_logs", "ix_gateway_access_logs_qr_code"):
        op.drop_index(
            "ix_gateway_access_logs_qr_code",
            table_name="gateway_access_logs",
        )
    if _has_index("gateway_access_logs", "ix_gateway_access_logs_gateway_visit_id"):
        op.drop_index(
            "ix_gateway_access_logs_gateway_visit_id",
            table_name="gateway_access_logs",
        )
    if _has_index("gateway_access_logs", "ix_gateway_access_logs_session_id"):
        op.drop_index(
            "ix_gateway_access_logs_session_id",
            table_name="gateway_access_logs",
        )
    if _has_index("gateway_access_logs", "ix_gateway_access_logs_zone_code"):
        op.drop_index(
            "ix_gateway_access_logs_zone_code",
            table_name="gateway_access_logs",
        )
    if _has_index("gateway_access_logs", "ix_gateway_access_logs_route_id"):
        op.drop_index(
            "ix_gateway_access_logs_route_id",
            table_name="gateway_access_logs",
        )
    if _has_table("gateway_access_logs"):
        op.drop_table("gateway_access_logs")

    if _has_index("gateway_routes", "ix_gateway_routes_enabled"):
        op.drop_index("ix_gateway_routes_enabled", table_name="gateway_routes")
    if _has_index("gateway_routes", "ix_gateway_routes_active_target"):
        op.drop_index(
            "ix_gateway_routes_active_target",
            table_name="gateway_routes",
        )
    if _has_index("gateway_routes", "ix_gateway_routes_zone_code"):
        op.drop_index("ix_gateway_routes_zone_code", table_name="gateway_routes")
    if _has_index("gateway_routes", "ix_gateway_routes_qr_code"):
        op.drop_index("ix_gateway_routes_qr_code", table_name="gateway_routes")
    if _has_table("gateway_routes"):
        op.drop_table("gateway_routes")

from __future__ import annotations

import argparse
import logging
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy import MetaData, inspect, literal, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError
from sqlalchemy.schema import CreateColumn
from sqlmodel import Session, SQLModel

from database import engine
from settings import settings


LOGGER = logging.getLogger("sonar.migrate")
ALEMBIC_VERSION_TABLE = "alembic_version"
PROJECT_ROOT = Path(__file__).resolve().parent
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"
MIGRATIONS_PATH = PROJECT_ROOT / "migrations"


@dataclass
class SchemaDrift:
    missing_tables: list[str] = field(default_factory=list)
    missing_columns: dict[str, list[str]] = field(default_factory=dict)
    missing_indexes: dict[str, list[str]] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not (
            self.missing_tables
            or self.missing_columns
            or self.missing_indexes
        )

    def summary(self) -> str:
        parts: list[str] = []
        if self.missing_tables:
            parts.append(f"missing tables={','.join(self.missing_tables[:8])}")
        if self.missing_columns:
            preview = [
                f"{table}:{','.join(columns[:8])}"
                for table, columns in sorted(self.missing_columns.items())
            ]
            parts.append(f"missing columns={'; '.join(preview[:8])}")
        if self.missing_indexes:
            preview = [
                f"{table}:{','.join(indexes[:8])}"
                for table, indexes in sorted(self.missing_indexes.items())
            ]
            parts.append(f"missing indexes={'; '.join(preview[:8])}")
        return "schema matches current SQLModel metadata" if not parts else " | ".join(parts)


@dataclass
class DatabaseState:
    table_names: list[str]
    user_tables: list[str]
    has_revision_table: bool
    revision_row_count: int
    current_revision: str | None
    known_revision: bool
    drift: SchemaDrift

    @property
    def is_empty(self) -> bool:
        return not self.user_tables and not self.has_revision_table

    def inconsistency_reason(self) -> str | None:
        if self.has_revision_table and self.revision_row_count != 1:
            return (
                f"{ALEMBIC_VERSION_TABLE} row count is {self.revision_row_count}, "
                "expected exactly 1"
            )
        if self.current_revision is None:
            if self.user_tables or self.has_revision_table:
                return "database has schema objects but no valid Alembic revision"
            return None
        if not self.known_revision:
            return f"database revision {self.current_revision!r} is not present in code"
        return None


def configure_logging() -> None:
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def alembic_config() -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(MIGRATIONS_PATH))
    config.set_main_option("prepend_sys_path", str(PROJECT_ROOT))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    return config


def script_directory(config: Config) -> ScriptDirectory:
    return ScriptDirectory.from_config(config)


def normalize_down_revisions(revision: Any) -> tuple[str, ...]:
    raw_value = revision.down_revision
    if raw_value is None:
        return ()
    if isinstance(raw_value, str):
        return (raw_value,)
    return tuple(item for item in raw_value if item is not None)


def assert_linear_migration_history(config: Config) -> list[str]:
    revisions = list(script_directory(config).walk_revisions())
    if not revisions:
        raise RuntimeError("Alembic has no revisions configured.")

    revision_ids = [revision.revision for revision in revisions]
    revision_id_set = set(revision_ids)
    root_revisions: list[str] = []

    for revision in revisions:
        parent_revisions = normalize_down_revisions(revision)
        if not parent_revisions:
            root_revisions.append(revision.revision)
            continue
        if len(parent_revisions) != 1:
            raise RuntimeError(
                "Alembic migration history must stay linear; "
                f"revision {revision.revision} has parents {parent_revisions}."
            )
        parent_revision = parent_revisions[0]
        if parent_revision not in revision_id_set:
            raise RuntimeError(
                "Alembic migration history is broken; "
                f"revision {revision.revision} references missing parent {parent_revision}."
            )

    if len(root_revisions) != 1:
        raise RuntimeError(
            "Alembic migration history must have exactly one base revision; "
            f"found {root_revisions}."
        )

    return revision_ids


def known_revisions(config: Config) -> set[str]:
    return set(assert_linear_migration_history(config))


def head_revision(config: Config) -> str:
    assert_linear_migration_history(config)
    heads = script_directory(config).get_heads()
    if not heads:
        raise RuntimeError("Alembic has no head revision configured.")
    if len(heads) > 1:
        raise RuntimeError(f"Alembic has multiple heads: {heads}")
    return heads[0]


def current_database_revision() -> str | None:
    with engine.connect() as connection:
        state = read_revision_state(connection)
        return state.current_revision


def read_revision_state(connection: Connection) -> DatabaseState:
    config = alembic_config()
    revisions = known_revisions(config)
    inspector = inspect(connection)
    table_names = sorted(inspector.get_table_names())
    has_revision_table = ALEMBIC_VERSION_TABLE in table_names
    revision_row_count = 0
    current_revision: str | None = None

    if has_revision_table:
        revision_row_count = connection.execute(
            text(f"SELECT COUNT(*) FROM {ALEMBIC_VERSION_TABLE}")
        ).scalar_one()
        if revision_row_count >= 1:
            current_revision = connection.execute(
                text(f"SELECT version_num FROM {ALEMBIC_VERSION_TABLE} LIMIT 1")
            ).scalar_one_or_none()

    drift = inspect_schema_drift(connection)
    user_tables = [name for name in table_names if name != ALEMBIC_VERSION_TABLE]
    return DatabaseState(
        table_names=table_names,
        user_tables=user_tables,
        has_revision_table=has_revision_table,
        revision_row_count=revision_row_count,
        current_revision=current_revision,
        known_revision=current_revision in revisions if current_revision else False,
        drift=drift,
    )


def inspect_schema_drift(connection: Connection) -> SchemaDrift:
    inspector = inspect(connection)
    existing_tables = set(inspector.get_table_names())
    expected_tables = {table.name for table in SQLModel.metadata.sorted_tables}
    missing_tables = sorted(expected_tables - existing_tables)

    missing_columns: dict[str, list[str]] = {}
    missing_indexes: dict[str, list[str]] = {}

    for table in SQLModel.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue

        existing_columns = {column["name"] for column in inspector.get_columns(table.name)}
        table_missing_columns = [
            column.name for column in table.columns if column.name not in existing_columns
        ]
        if table_missing_columns:
            missing_columns[table.name] = table_missing_columns

        existing_indexes = {index["name"] for index in inspector.get_indexes(table.name)}
        table_missing_indexes = [
            index.name
            for index in sorted(table.indexes, key=lambda item: item.name or "")
            if index.name and index.name not in existing_indexes
        ]
        if table_missing_indexes:
            missing_indexes[table.name] = table_missing_indexes

    return SchemaDrift(
        missing_tables=missing_tables,
        missing_columns=missing_columns,
        missing_indexes=missing_indexes,
    )


def schema_matches_current_models() -> tuple[bool, str]:
    with engine.connect() as connection:
        drift = inspect_schema_drift(connection)
    return drift.is_empty, drift.summary()


def wait_for_database() -> None:
    deadline = time.monotonic() + settings.startup_dependency_timeout_seconds
    attempt = 0
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        attempt += 1
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            LOGGER.info("Database connection established on attempt %s.", attempt)
            return
        except OperationalError as exc:
            last_error = exc
            LOGGER.warning(
                "Database unavailable on attempt %s; retrying in %.1fs: %s",
                attempt,
                settings.startup_dependency_retry_interval_seconds,
                exc,
            )
            time.sleep(settings.startup_dependency_retry_interval_seconds)

    raise RuntimeError("Database connection could not be established within startup timeout.") from last_error


@contextmanager
def migration_advisory_lock() -> Iterator[None]:
    if engine.dialect.name != "postgresql":
        yield
        return

    deadline = time.monotonic() + settings.migration_lock_timeout_seconds
    connection = engine.connect()
    acquired = False
    try:
        while time.monotonic() < deadline:
            acquired = bool(
                connection.execute(
                    text("SELECT pg_try_advisory_lock(:lock_key)"),
                    {"lock_key": settings.migration_lock_key},
                ).scalar_one()
            )
            if acquired:
                LOGGER.info(
                    "Acquired PostgreSQL migration advisory lock %s.",
                    settings.migration_lock_key,
                )
                break
            LOGGER.info(
                "Waiting for PostgreSQL migration advisory lock %s.",
                settings.migration_lock_key,
            )
            time.sleep(settings.migration_lock_retry_interval_seconds)

        if not acquired:
            raise TimeoutError(
                "Timed out waiting for PostgreSQL migration advisory lock."
            )

        yield
    finally:
        if acquired:
            try:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": settings.migration_lock_key},
                )
                LOGGER.info(
                    "Released PostgreSQL migration advisory lock %s.",
                    settings.migration_lock_key,
                )
            except Exception:  # noqa: BLE001
                LOGGER.exception("Failed to release PostgreSQL migration advisory lock.")
        connection.close()


def upgrade_to_head(config: Config) -> None:
    target = head_revision(config)
    LOGGER.info("Running alembic upgrade to %s.", target)
    command.upgrade(config, target)


def stamp_database_revision(version_num: str) -> None:
    LOGGER.warning("Stamping database revision to %s.", version_num)
    with engine.begin() as connection:
        inspector = inspect(connection)
        if ALEMBIC_VERSION_TABLE not in inspector.get_table_names():
            connection.execute(
                text(
                    f"CREATE TABLE {ALEMBIC_VERSION_TABLE} "
                    "(version_num VARCHAR(32) NOT NULL)"
                )
            )
        else:
            connection.execute(text(f"DELETE FROM {ALEMBIC_VERSION_TABLE}"))
        connection.execute(
            text(
                f"INSERT INTO {ALEMBIC_VERSION_TABLE} (version_num) "
                "VALUES (:version_num)"
            ),
            {"version_num": version_num},
        )


def reset_schema() -> None:
    LOGGER.warning("RESET_DB enabled; dropping database objects before migration.")
    with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
            return

        reflected = MetaData()
        reflected.reflect(bind=connection)
        if reflected.tables:
            reflected.drop_all(bind=connection)


def sql_default_literal(
    connection: Connection,
    table_name: str,
    column_name: str,
) -> str | None:
    metadata_column = SQLModel.metadata.tables[table_name].columns[column_name]

    server_default = metadata_column.server_default
    if server_default is not None:
        arg = getattr(server_default, "arg", None)
        if arg is not None:
            try:
                return str(
                    arg.compile(
                        dialect=connection.dialect,
                        compile_kwargs={"literal_binds": True},
                    )
                )
            except Exception:  # noqa: BLE001
                LOGGER.debug(
                    "Could not compile server default for %s.%s; falling back.",
                    table_name,
                    column_name,
                )

    column_default = metadata_column.default
    if column_default is None:
        return None

    if getattr(column_default, "is_scalar", False):
        value = column_default.arg
    else:
        # Callable defaults like make_uuid()/utcnow() are great for new writes,
        # but unsafe to materialize once for all legacy rows during repair.
        return None

    return str(
        literal(value).compile(
            dialect=connection.dialect,
            compile_kwargs={"literal_binds": True},
        )
    )


def repaired_column_sql(
    connection: Connection,
    table_name: str,
    column_name: str,
) -> str:
    metadata_table = SQLModel.metadata.tables[table_name]
    metadata_column = metadata_table.columns[column_name]
    column_sql = str(CreateColumn(metadata_column).compile(dialect=connection.dialect))
    if connection.dialect.name != "sqlite" or metadata_column.nullable:
        return column_sql

    default_sql = sql_default_literal(connection, table_name, column_name)
    if default_sql is not None and " NOT NULL" in column_sql and " DEFAULT " not in column_sql:
        return column_sql.replace(" NOT NULL", f" DEFAULT {default_sql} NOT NULL")

    if default_sql is None and " NOT NULL" in column_sql:
        # SQLite cannot add a NOT NULL column to a populated legacy table unless
        # a default is available. We relax nullability for repaired historical
        # rows so the schema repair can converge and new writes can use the
        # current application defaults.
        return column_sql.replace(" NOT NULL", "")

    return column_sql


def add_missing_column(connection: Connection, table_name: str, column_name: str) -> None:
    column_sql = repaired_column_sql(connection, table_name, column_name)
    quoted_table = connection.dialect.identifier_preparer.quote(table_name)
    LOGGER.warning("Repairing missing column %s.%s.", table_name, column_name)
    connection.execute(text(f"ALTER TABLE {quoted_table} ADD COLUMN {column_sql}"))


def reconcile_schema_drift() -> SchemaDrift:
    with engine.begin() as connection:
        drift = inspect_schema_drift(connection)
        if drift.is_empty:
            LOGGER.info("No schema drift detected; no physical repair needed.")
            return drift

        LOGGER.warning("Schema drift detected before repair: %s", drift.summary())

        for table in SQLModel.metadata.sorted_tables:
            if table.name in drift.missing_tables:
                LOGGER.warning("Creating missing table %s.", table.name)
                table.create(bind=connection, checkfirst=True)

        drift = inspect_schema_drift(connection)

        for table_name, column_names in drift.missing_columns.items():
            for column_name in column_names:
                add_missing_column(connection, table_name, column_name)

        drift = inspect_schema_drift(connection)

        for table in SQLModel.metadata.sorted_tables:
            missing_index_names = set(drift.missing_indexes.get(table.name, []))
            if not missing_index_names:
                continue
            index_by_name = {
                index.name: index for index in table.indexes if index.name is not None
            }
            for index_name in sorted(missing_index_names):
                LOGGER.warning("Creating missing index %s on %s.", index_name, table.name)
                index_by_name[index_name].create(bind=connection, checkfirst=True)

        final_drift = inspect_schema_drift(connection)
        if final_drift.is_empty:
            LOGGER.info("Schema repair converged to current SQLModel metadata.")
        else:
            LOGGER.error("Schema repair incomplete: %s", final_drift.summary())
        return final_drift


def repair_inconsistent_database(config: Config, state: DatabaseState) -> None:
    reason = state.inconsistency_reason() or "unknown inconsistency"
    target = head_revision(config)
    LOGGER.error("Detected inconsistent database state: %s", reason)

    if not state.drift.is_empty:
        reconcile_schema_drift()

    stamp_database_revision(target)
    upgrade_to_head(config)

    post_upgrade_state = inspect_database_state(config)
    if not post_upgrade_state.drift.is_empty:
        LOGGER.warning(
            "Schema drift remains after stamp/upgrade; applying structural repair: %s",
            post_upgrade_state.drift.summary(),
        )
        reconcile_schema_drift()
        stamp_database_revision(target)
        upgrade_to_head(config)


def inspect_database_state(config: Config) -> DatabaseState:
    _ = config
    with engine.connect() as connection:
        return read_revision_state(connection)


def validate_final_state(config: Config, *, strict: bool) -> bool:
    target = head_revision(config)
    state = inspect_database_state(config)
    valid = True
    inconsistency_reason = state.inconsistency_reason()

    if state.current_revision != target:
        valid = False
        LOGGER.error(
            "Alembic validation failed: current revision is %r but head is %r.",
            state.current_revision,
            target,
        )

    if inconsistency_reason is not None:
        valid = False
        LOGGER.error("Alembic validation found inconsistent revision state: %s", inconsistency_reason)

    if not state.drift.is_empty:
        valid = False
        LOGGER.error("Schema validation failed: %s", state.drift.summary())

    if valid:
        LOGGER.info(
            "Alembic validation succeeded: current=%s head=%s.",
            state.current_revision,
            target,
        )
        return True

    if strict:
        raise RuntimeError("Database validation failed after migration.")
    return False


def apply_migrations(*, reset_requested: bool = False, strict: bool = False) -> bool:
    configure_logging()
    config = alembic_config()
    try:
        wait_for_database()
        with migration_advisory_lock():
            target = head_revision(config)
            LOGGER.info("Migration target head is %s.", target)

            if reset_requested:
                reset_schema()
                upgrade_to_head(config)
                return validate_final_state(config, strict=strict)

            state = inspect_database_state(config)
            LOGGER.info(
                "Pre-migration state: revision=%r tables=%s drift=%s",
                state.current_revision,
                len(state.user_tables),
                state.drift.summary(),
            )

            if state.is_empty:
                LOGGER.info("Empty database detected; running upgrade head.")
                upgrade_to_head(config)
            else:
                reason = state.inconsistency_reason()
                if reason is not None:
                    repair_inconsistent_database(config, state)
                else:
                    try:
                        upgrade_to_head(config)
                    except CommandError as exc:
                        message = str(exc)
                        if (
                            "Can't locate revision identified by" not in message
                            and "No such revision or branch" not in message
                        ):
                            raise
                        LOGGER.error(
                            "Alembic upgrade hit revision lookup failure; applying repair path: %s",
                            message,
                        )
                        repair_inconsistent_database(config, inspect_database_state(config))

            return validate_final_state(config, strict=strict)
    except Exception:  # noqa: BLE001
        LOGGER.exception("Migration pipeline failed.")
        if strict:
            raise
        return False


def seed_demo() -> None:
    if not settings.auto_bootstrap_demo_data or not settings.database_is_sqlite:
        return

    from main import bootstrap_demo_data

    with Session(engine) as session:
        try:
            bootstrap_demo_data(session)
        except Exception:  # noqa: BLE001
            session.rollback()
            LOGGER.error(
                "Demo bootstrap failed during migrate.py; continuing because runtime bootstrap can recover."
            )
            traceback.print_exc()


def main() -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="Apply SONAR migrations and optional demo seeding.")
    parser.add_argument("--reset", action="store_true", help="Drop schema before applying migrations.")
    parser.add_argument(
        "--skip-demo-seed",
        action="store_true",
        help="Do not create demo pulseras/roots after migrating.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if the final revision or schema validation does not converge.",
    )
    args = parser.parse_args()

    reset_requested = args.reset or settings.reset_db
    migrated = apply_migrations(reset_requested=reset_requested, strict=args.strict)

    if migrated and not args.skip_demo_seed:
        seed_demo()

    if migrated:
        LOGGER.info("Migration pipeline completed successfully.")
        return 0

    LOGGER.error("Migration pipeline completed with warnings; API startup may rely on runtime recovery.")
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())

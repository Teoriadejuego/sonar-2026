from __future__ import annotations

import argparse

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel

from database import engine
from main import bootstrap_demo_data


def alembic_config() -> Config:
    return Config("alembic.ini")


def script_directory(config: Config) -> ScriptDirectory:
    return ScriptDirectory.from_config(config)


def known_revisions(config: Config) -> set[str]:
    return {revision.revision for revision in script_directory(config).walk_revisions()}


def head_revision(config: Config) -> str:
    heads = script_directory(config).get_heads()
    if not heads:
        raise RuntimeError("Alembic has no head revision configured.")
    if len(heads) > 1:
        raise RuntimeError(f"Alembic has multiple heads: {heads}")
    return heads[0]


def current_database_revision() -> str | None:
    with engine.connect() as connection:
        inspector = inspect(connection)
        if "alembic_version" not in inspector.get_table_names():
            return None
        result = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        return result.scalar_one_or_none()


def schema_matches_current_models() -> tuple[bool, str]:
    with engine.connect() as connection:
        inspector = inspect(connection)
        existing_tables = set(inspector.get_table_names())
        expected_tables = {table.name for table in SQLModel.metadata.sorted_tables}
        missing_tables = sorted(expected_tables - existing_tables)
        if missing_tables:
            return False, f"missing tables: {', '.join(missing_tables[:8])}"

        for table in SQLModel.metadata.sorted_tables:
            existing_columns = {column["name"] for column in inspector.get_columns(table.name)}
            expected_columns = {column.name for column in table.columns}
            missing_columns = sorted(expected_columns - existing_columns)
            if missing_columns:
                preview = ", ".join(missing_columns[:8])
                return False, f"table {table.name} missing columns: {preview}"

    return True, "schema matches current SQLModel metadata"


def stamp_database_revision(version_num: str) -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "alembic_version" not in inspector.get_table_names():
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        else:
            connection.execute(text("DELETE FROM alembic_version"))
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:version_num)"),
            {"version_num": version_num},
        )


def repair_unknown_revision_if_possible(config: Config) -> bool:
    current_revision = current_database_revision()
    if current_revision is None:
        return False

    revisions = known_revisions(config)
    if current_revision in revisions:
        return False

    schema_ok, detail = schema_matches_current_models()
    if not schema_ok:
        raise RuntimeError(
            "Database revision table references an unknown Alembic revision "
            f"({current_revision!r}) and automatic repair was refused because {detail}."
        )

    target_revision = head_revision(config)
    stamp_database_revision(target_revision)
    print(
        "Recovered alembic_version from unknown revision "
        f"{current_revision!r} to current head {target_revision!r} because the live schema already matches."
    )
    return True


def apply_migrations() -> None:
    config = alembic_config()
    repair_unknown_revision_if_possible(config)
    try:
        command.upgrade(config, "head")
    except CommandError as exc:
        message = str(exc)
        if "Can't locate revision identified by" not in message and "No such revision or branch" not in message:
            raise
        if not repair_unknown_revision_if_possible(config):
            raise
        command.upgrade(config, "head")


def reset_schema() -> None:
    SQLModel.metadata.drop_all(engine)
    apply_migrations()


def seed_demo() -> None:
    with Session(engine) as session:
        bootstrap_demo_data(session)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply SONAR migrations and optional demo seeding.")
    parser.add_argument("--reset", action="store_true", help="Drop schema before applying migrations.")
    parser.add_argument("--skip-demo-seed", action="store_true", help="Do not create demo pulseras/roots after migrating.")
    args = parser.parse_args()

    if args.reset:
        reset_schema()
    else:
        apply_migrations()

    if not args.skip_demo_seed:
        seed_demo()

    print("Migrations applied successfully.")


if __name__ == "__main__":
    main()

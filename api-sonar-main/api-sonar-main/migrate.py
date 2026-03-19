from __future__ import annotations

import argparse

from alembic import command
from alembic.config import Config
from sqlmodel import Session, SQLModel

from database import engine
from main import bootstrap_demo_data


def alembic_config() -> Config:
    return Config("alembic.ini")


def apply_migrations() -> None:
    command.upgrade(alembic_config(), "head")


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

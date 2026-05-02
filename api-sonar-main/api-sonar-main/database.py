from sqlalchemy import event, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from settings import settings


def sqlite_uses_inmemory_database(database_url: str) -> bool:
    normalized = database_url.lower()
    return (
        normalized in {"sqlite://", "sqlite:///:memory:"}
        or ":memory:" in normalized
        or "mode=memory" in normalized
    )


connect_args = {}
engine_kwargs = {
    "pool_pre_ping": True,
    "echo": settings.sql_echo,
}
if settings.database_is_sqlite:
    connect_args.update(
        {
            "check_same_thread": False,
            "timeout": settings.db_sqlite_busy_timeout_seconds,
        }
    )
    if sqlite_uses_inmemory_database(settings.database_url):
        engine_kwargs["poolclass"] = StaticPool
    else:
        engine_kwargs.update(
            {
                "pool_size": settings.db_pool_size,
                "max_overflow": settings.db_max_overflow,
                "pool_timeout": settings.db_pool_timeout_seconds,
                "pool_recycle": settings.db_pool_recycle_seconds,
            }
        )
else:
    connect_args["connect_timeout"] = settings.db_connect_timeout_seconds
    engine_kwargs.update(
        {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_timeout": settings.db_pool_timeout_seconds,
            "pool_recycle": settings.db_pool_recycle_seconds,
        }
    )
engine_kwargs["connect_args"] = connect_args

engine = create_engine(settings.database_url, **engine_kwargs)


if settings.database_is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_session():
    with Session(engine, expire_on_commit=False) as session:
        yield session


def database_ready() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False

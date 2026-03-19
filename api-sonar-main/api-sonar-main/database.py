from sqlalchemy import text
from sqlmodel import Session, create_engine

from settings import settings


connect_args = {"check_same_thread": False} if settings.database_is_sqlite else {}
engine_kwargs = {
    "pool_pre_ping": True,
    "echo": settings.sql_echo,
    "connect_args": connect_args,
}
if not settings.database_is_sqlite:
    engine_kwargs.update(
        {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_timeout": settings.db_pool_timeout_seconds,
            "pool_recycle": settings.db_pool_recycle_seconds,
        }
    )

engine = create_engine(settings.database_url, **engine_kwargs)


def get_session():
    with Session(engine) as session:
        yield session


def database_ready() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False

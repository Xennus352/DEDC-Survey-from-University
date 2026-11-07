from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

from app.config import settings

engine_options = {
    "pool_pre_ping": True,
    "pool_recycle": 1_800,
    "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
}
if settings.DATABASE_URL.startswith(("mysql+pymysql", "mariadb+pymysql")):
    engine_options["connect_args"] = {
        "connect_timeout": settings.DATABASE_CONNECT_TIMEOUT,
        "read_timeout": settings.DATABASE_READ_TIMEOUT,
        "write_timeout": settings.DATABASE_WRITE_TIMEOUT,
    }

engine = create_engine(settings.DATABASE_URL, **engine_options)
Base = declarative_base()


def SessionLocal():
    """Open an eight-table unit of work; Base is a transient query model only."""
    from app.storage.compact import CompactSession
    return CompactSession(engine, settings.PRIVATE_STORAGE_DIR)

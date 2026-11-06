from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)
Base = declarative_base()


def SessionLocal():
    """Use existing DEDC tables; Base is a transient query model only."""
    from app.storage.compact import CompactSession
    return CompactSession(engine, settings.PRIVATE_STORAGE_DIR, settings.METADATA_STORAGE)

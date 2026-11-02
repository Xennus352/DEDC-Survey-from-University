from alembic import context
from sqlalchemy import create_engine, pool
from app.config import settings
from app.database import Base
import app.models  # Register the complete schema, including preserved legacy tables.

if context.is_offline_mode():
    raise RuntimeError(
        "These guarded migrations require an online connection to inspect existing tables."
    )
engine = create_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
with engine.connect() as connection:
    context.configure(
        connection=connection, target_metadata=Base.metadata, compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()

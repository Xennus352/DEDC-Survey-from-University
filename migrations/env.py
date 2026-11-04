from alembic import context
from sqlalchemy import create_engine, pool, inspect
from app.config import settings
from app.database import Base
import app.models  # Register the complete schema, including preserved legacy tables.

if context.is_offline_mode():
    raise RuntimeError(
        "These guarded migrations require an online connection to inspect existing tables."
    )
engine = create_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
with engine.connect() as connection:
    from app.storage.schema import metadata as persistent_metadata
    if set(inspect(connection).get_table_names()) == set(persistent_metadata.tables):
        raise RuntimeError(
            "This is the eight-table DEDC schema. Historical Alembic migrations "
            "must not be applied; see docs/database-tables.md."
        )
    connection.commit()
    context.configure(
        connection=connection, target_metadata=Base.metadata, compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()

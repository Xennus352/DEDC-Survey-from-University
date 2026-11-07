import logging

from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.errors import SurveyDatabaseUnavailable

logger = logging.getLogger(__name__)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_survey_connection():
    """Yield a transactional connection for the public survey tables."""
    try:
        with engine.begin() as connection:
            yield connection
    except (OperationalError, InterfaceError, SQLAlchemyTimeoutError) as error:
        logger.error("Survey database connection failed: %s", error)
        raise SurveyDatabaseUnavailable() from error

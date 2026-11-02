from sqlalchemy import BigInteger, Column, Integer, String

from app.database import Base


class AdminSession(Base):
    """Only a hash of the browser's session token is stored in the database."""

    __tablename__ = "admin_sessions"

    token_hash = Column(String(64), primary_key=True)
    user_id = Column(Integer, nullable=True)
    expires_at = Column(BigInteger, nullable=False, index=True)

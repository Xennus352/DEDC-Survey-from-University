"""Map the existing DEDC Docker database account tables without renaming columns."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func

from app.database import Base


class UserRole(Base):
    __tablename__ = "userrole"

    id = Column("roleId", Integer, primary_key=True)
    name = Column("roleName", String(100), nullable=False)


class User(Base):
    __tablename__ = "user"

    id = Column("userId", Integer, primary_key=True)
    role_id = Column("roleId", Integer, ForeignKey("userrole.roleId"), nullable=False)
    university_id = Column("uniId", Integer, nullable=True)
    ministry_id = Column("ministryId", Integer, nullable=True)
    username = Column("userName", String(100), nullable=False)
    password_hash = Column("passwordHash", String(255), nullable=False)
    is_active = Column("isActive", Boolean, nullable=False, default=True)
    created_at = Column("createdAt", DateTime, server_default=func.now(), nullable=False)

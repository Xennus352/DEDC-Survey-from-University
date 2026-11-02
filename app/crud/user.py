from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User, UserRole
from app.portal_auth import verify_password


def admin_query(db: Session):
    return db.query(User).join(UserRole, User.role_id == UserRole.id).filter(
        User.is_active.is_(True), UserRole.name == settings.ADMIN_ROLE_NAME,
    )


def find_admin(db: Session, user_id: int) -> User | None:
    return admin_query(db).filter(User.id == user_id).first()


def authenticate_admin(db: Session, username: str, password: str) -> User | None:
    user = admin_query(db).filter(User.username == username).first()
    # Do the same password work for an unknown account to avoid a fast rejection.
    password_hash = user.password_hash if user else (
        "pbkdf2_sha256$600000$dummy-salt$" + "0" * 64
    )
    valid = verify_password(password, password_hash)
    return user if valid else None


def authenticate_account(db: Session, username: str, password: str) -> User | None:
    account=db.query(User).filter(User.username==username,User.is_active.is_(True)).first()
    password_hash=account.password_hash if account else ('pbkdf2_sha256$600000$dummy-salt$'+'0'*64)
    return account if verify_password(password,password_hash) else None

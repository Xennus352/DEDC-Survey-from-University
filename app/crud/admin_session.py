import hashlib
import secrets
import time

from sqlalchemy.orm import Session

from app.models.admin_session import AdminSession


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def find_session(db: Session, token: str) -> AdminSession | None:
    session = db.get(AdminSession, token_hash(token))
    if session and session.expires_at > time.time():
        return session
    return None


def delete_session(db: Session, token: str) -> None:
    session = db.get(AdminSession, token_hash(token))
    if session:
        db.delete(session)
    db.commit()


def create_session(db: Session, user_id: int | None = None) -> str:
    db.query(AdminSession).filter(AdminSession.expires_at <= time.time()).delete()
    token = secrets.token_urlsafe(32)
    lifetime = 8 * 60 * 60 if user_id is not None else 15 * 60
    db.add(AdminSession(
        token_hash=token_hash(token),
        user_id=user_id,
        expires_at=int(time.time()) + lifetime,
    ))
    db.commit()
    return token

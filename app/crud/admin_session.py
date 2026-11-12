import hashlib
import secrets
import time
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.admin_session import AdminSession


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _exec_native(db: Session, sql: str, params: dict) -> bool:
    """Execute SQL on native connection if table exists. Returns True if executed."""
    native = getattr(db, 'native', None)
    if native is None:
        return False
    try:
        native.execute(text(sql), params)
        native.commit()
        return True
    except OperationalError as e:
        if "no such table" in str(e).lower() or "doesn't exist" in str(e).lower():
            return False
        raise


def find_session(db: Session, token: str) -> Optional[AdminSession]:
    # First check ORM projection
    session = db.get(AdminSession, token_hash(token))
    if session and session.expires_at > time.time():
        return session
    # Fallback: check native database directly
    native = getattr(db, 'native', None)
    if native is not None:
        from sqlalchemy import text
        th = token_hash(token)
        row = native.execute(
            text("SELECT token_hash, user_id, expires_at FROM admin_sessions WHERE token_hash = :th AND expires_at > :now"),
            {"th": th, "now": int(time.time())}
        ).first()
        if row:
            # Create a detached AdminSession object
            return AdminSession(token_hash=row.token_hash, user_id=row.user_id, expires_at=row.expires_at)
    return None


def delete_session(db: Session, token: str) -> None:
    session = db.get(AdminSession, token_hash(token))
    if session:
        db.delete(session)
    db.commit()
    # Also delete from native database if table exists
    _exec_native(db, "DELETE FROM admin_sessions WHERE token_hash = :th", {"th": token_hash(token)})


def create_session(db: Session, user_id: int | None = None) -> str:
    # Clean up expired sessions in both ORM and native
    native = getattr(db, 'native', None)
    now = int(time.time())
    if native is not None:
        try:
            native.execute(text("DELETE FROM admin_sessions WHERE expires_at <= :now"), {"now": now})
            native.commit()
        except OperationalError as e:
            if "no such table" not in str(e).lower() and "doesn't exist" not in str(e).lower():
                raise
    else:
        db.query(AdminSession).filter(AdminSession.expires_at <= now).delete()

    token = secrets.token_urlsafe(32)
    lifetime = 8 * 60 * 60 if user_id is not None else 15 * 60
    expires_at = now + lifetime
    th = token_hash(token)

    # Add to ORM projection
    db.add(AdminSession(
        token_hash=th,
        user_id=user_id,
        expires_at=expires_at,
    ))

    # Also write directly to native database if table exists
    _exec_native(db,
        "INSERT INTO admin_sessions (token_hash, user_id, expires_at) VALUES (:th, :uid, :exp)",
        {"th": th, "uid": user_id, "exp": expires_at}
    )

    db.commit()
    return token
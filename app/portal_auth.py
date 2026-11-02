"""Password and CSRF helpers shared by the portal routes."""

import hashlib
import hmac
import secrets

PASSWORD_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PASSWORD_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = password_hash.split("$")
        if algorithm != "pbkdf2_sha256" or int(iterations) != PASSWORD_ITERATIONS:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), PASSWORD_ITERATIONS,
        ).hex()
        return hmac.compare_digest(actual.encode(), expected.encode())
    except ValueError:
        return False


def csrf_token(session_token: str) -> str:
    return hmac.new(session_token.encode(), b"portal-csrf", "sha256").hexdigest()


if __name__ == "__main__":
    from getpass import getpass

    from app.config import settings
    from app.database import SessionLocal
    from app.models.user import User, UserRole

    username = input("Admin username: ").strip()
    if not username or len(username) > 100:
        raise SystemExit("Use a username between 1 and 100 characters.")
    password = getpass("Admin password: ")
    if len(password) < 8:
        raise SystemExit("Use a password with at least 8 characters.")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match.")
    with SessionLocal() as db:
        if db.query(User).filter(User.username == username).first():
            raise SystemExit("That username already exists. No changes were made.")
        role = db.query(UserRole).filter(UserRole.name == settings.ADMIN_ROLE_NAME).first()
        if role is None:
            role = UserRole(name=settings.ADMIN_ROLE_NAME)
            db.add(role)
            db.flush()
        db.add(User(username=username, password_hash=hash_password(password), role_id=role.id))
        db.commit()
    print("Administrator account created in the DEDC database.")

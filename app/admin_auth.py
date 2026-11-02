"""Shared session authorization for the entire administrator URL namespace."""

import hmac
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, RedirectResponse

from app.crud import admin_session, user
from app.database import SessionLocal
from app.dependencies import get_db
from app.portal_auth import csrf_token

COOKIE_NAME = "dedc_portal_session"


@dataclass(frozen=True)
class AdminIdentity:
    id: int
    username: str
    role_id: int


def authorize(db: Session, token: str) -> AdminIdentity:
    session = admin_session.find_session(db, token)
    if not session or session.user_id is None:
        raise HTTPException(401, "Your session expired. Sign in again.")
    admin = user.find_admin(db, session.user_id)
    if not admin:
        raise HTTPException(403, "Administrator access is required.")
    return AdminIdentity(admin.id, admin.username, admin.role_id)


def require_admin(request: Request, db: Session = Depends(get_db)) -> AdminIdentity:
    identity = getattr(request.state, "admin", None)
    return identity or authorize(db, request.cookies.get(COOKIE_NAME, ""))


def inspect_session(token: str) -> AdminIdentity:
    # Each worker owns and closes its session; never share a Session across requests.
    with SessionLocal() as db:
        return authorize(db, token)


class AdminAuthorizationMiddleware:
    """Guard known and future admin paths before route dispatch, including 404s."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        page = path == "/dashboard" or path.startswith("/dashboard/")
        api = path == "/api/admin" or path.startswith("/api/admin/")
        if scope["type"] not in {"http", "websocket"} or not (page or api):
            await self.app(scope, receive, send)
            return
        request = Request(scope) if scope["type"] == "http" else None
        if request is None:
            # No authenticated WebSocket features exist. Do not admit future sockets
            # without a connection-level revocation policy.
            await send({"type": "websocket.close", "code": 4403})
            return
        token = request.cookies.get(COOKIE_NAME, "")
        try:
            identity = await run_in_threadpool(inspect_session, token)
            if scope["method"] not in {"GET", "HEAD", "OPTIONS"}:
                supplied = request.headers.get("x-csrf-token", "")
                if not hmac.compare_digest(
                    supplied.encode(), csrf_token(token).encode()
                ):
                    raise HTTPException(403, "Invalid CSRF token.")
            scope.setdefault("state", {})["admin"] = identity
        except HTTPException as error:
            if (
                page
                and error.status_code in {401, 403}
                and scope["method"] in {"GET", "HEAD"}
            ):
                response = RedirectResponse(
                    str(request.base_url) + "portal", status_code=303
                )
            else:
                response = JSONResponse(
                    {"detail": error.detail}, status_code=error.status_code
                )
            response.headers["Cache-Control"] = "no-store"
            await response(scope, receive, send)
            return

        async def private_send(message):
            if message["type"] == "http.response.start":
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() not in {b"cache-control", b"pragma", b"expires"}
                ]
                headers.extend(
                    [
                        (b"cache-control", b"no-store"),
                        (b"pragma", b"no-cache"),
                        (b"expires", b"0"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"same-origin"),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, private_send)


def require_respondent(request: Request, db: Session = Depends(get_db)):
    from app.models.user import User

    session = admin_session.find_session(db, request.cookies.get(COOKIE_NAME, ""))
    account = db.get(User, session.user_id) if session and session.user_id else None
    if not account or not account.is_active:
        raise HTTPException(401, "Sign in to submit this survey.")
    return account


def require_survey_csrf(request: Request, account=Depends(require_respondent)):
    token = request.cookies.get(COOKIE_NAME, "")
    if not hmac.compare_digest(
        request.headers.get("x-csrf-token", "").encode(), csrf_token(token).encode()
    ):
        raise HTTPException(403, "Invalid CSRF token.")
    return account

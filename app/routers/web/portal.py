"""Admin HTML routes, isolated from the public landing page."""

import hmac
from contextlib import asynccontextmanager
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.admin_auth import COOKIE_NAME, AdminIdentity, require_admin
from app.config import settings
from app.crud import admin_session, user
from app.database import engine
from app.dependencies import get_db
from app.models.admin_session import AdminSession
from app.portal_auth import csrf_token
from app.routers.web.views import templates


@asynccontextmanager
async def lifespan(app):
    # Persistent sessions live in private files referenced by the eight-table
    # store. Never create the ORM's transient projection tables in DATABASE_URL.
    yield


router = APIRouter(tags=["portal"], lifespan=lifespan)


def render(request: Request, template: str, token: str, status_code=200, **context):
    response = templates.TemplateResponse(
        request=request,
        name=f"portal/{template}.html",
        context={"csrf_token": csrf_token(token), **context},
        status_code=status_code,
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    return response


def set_session_cookie(response, token: str, authenticated=False):
    # Clear the old portal-only cookie when upgrading to the separate dashboard.
    response.delete_cookie(
        COOKIE_NAME, path="/portal", httponly=True, samesite="strict",
        secure=settings.PORTAL_COOKIE_SECURE,
    )
    response.set_cookie(
        COOKIE_NAME, token, path="/", httponly=True, samesite="strict",
        secure=settings.PORTAL_COOKIE_SECURE,
        max_age=8 * 60 * 60 if authenticated else 15 * 60,
    )


def current_admin(request: Request, db: Session):
    session = admin_session.find_session(db, request.cookies.get(COOKIE_NAME, ""))
    if session and session.user_id is not None:
        return user.find_admin(db, session.user_id)
    return None


def redirect_to(request: Request, route_name: str):
    response = RedirectResponse(request.url_for(route_name), status_code=303)
    response.headers["Cache-Control"] = "no-store"
    return response


async def read_form(request: Request, db: Session) -> dict[str, str]:
    if request.headers.get("content-type", "").split(";")[0] != "application/x-www-form-urlencoded":
        raise HTTPException(415, "Submit the portal form as URL-encoded data.")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 8192:
            raise HTTPException(413, "Form is too large.")
    try:
        fields = parse_qs(body.decode("utf-8"), max_num_fields=10)
    except (UnicodeDecodeError, ValueError):
        raise HTTPException(400, "Invalid form.")
    form = {key: values[0] for key, values in fields.items() if len(values) == 1}
    token = request.cookies.get(COOKIE_NAME, "")
    if not admin_session.find_session(db, token) or not hmac.compare_digest(
        form.get("csrf_token", "").encode(), csrf_token(token).encode(),
    ):
        raise HTTPException(403, "This form expired. Reload /portal and try again.")
    return form


@router.get("/portal", name="portal")
def portal(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME, "")
    session = admin_session.find_session(db, token)
    admin = current_admin(request, db)
    if admin:
        response = redirect_to(request, "dashboard")
        set_session_cookie(response, token, authenticated=True)
        return response
    if not session or session.user_id is not None:
        admin_session.delete_session(db, token)
        token = admin_session.create_session(db)
    response = render(request, "login", token)
    set_session_cookie(response, token)
    return response


@router.get("/dashboard", name="dashboard")
def dashboard(request: Request, admin: AdminIdentity = Depends(require_admin)):
    return render(
        request, "dashboard", request.cookies[COOKIE_NAME], username=admin.username, page="overview", page_title="Overview",
    )


@router.get("/portal/login", name="portal_login_page")
def login_page(request: Request, db: Session = Depends(get_db)):
    return portal(request, db)


@router.post("/portal/login", name="portal_login")
async def login(request: Request, db: Session = Depends(get_db)):
    if current_admin(request, db):
        response = redirect_to(request, "dashboard")
        set_session_cookie(response, request.cookies[COOKIE_NAME], authenticated=True)
        return response
    form = await read_form(request, db)
    token = request.cookies[COOKIE_NAME]
    admin = await run_in_threadpool(
        user.authenticate_admin, db, form.get("username", ""), form.get("password", ""),
    )
    if not admin:
        from app.services.forms import audit
        audit(db,None,'auth.login_failed','session',None)
        db.commit()
        return render(
            request, "login", token, status_code=401,
            error="The username or password is incorrect.",
            username=form.get("username", ""),
        )
    admin_id = admin.id
    from app.services.forms import audit
    audit(db,admin_id,'auth.login','user',admin_id)
    admin_session.delete_session(db, token)
    token = admin_session.create_session(db, admin_id)
    response = redirect_to(request, "dashboard")
    set_session_cookie(response, token, authenticated=True)
    return response


@router.post("/portal/logout", name="portal_logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    await read_form(request, db)
    from app.services.forms import audit
    session=admin_session.find_session(db,request.cookies[COOKIE_NAME])
    audit(db,session.user_id if session else None,'auth.logout','session',None)
    admin_session.delete_session(db, request.cookies[COOKIE_NAME])
    response = redirect_to(request, "portal")
    response.delete_cookie(
        COOKIE_NAME, path="/", secure=settings.PORTAL_COOKIE_SECURE,
        httponly=True, samesite="strict",
    )
    response.delete_cookie(
        COOKIE_NAME, path="/portal", secure=settings.PORTAL_COOKIE_SECURE,
        httponly=True, samesite="strict",
    )
    return response

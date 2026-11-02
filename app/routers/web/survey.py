"""Respondent login and the real survey experience, sharing the preview renderer."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from app.admin_auth import COOKIE_NAME, require_respondent
from app.crud import admin_session, user
from app.dependencies import get_db
from app.portal_auth import csrf_token
from app.routers.web.portal import read_form, set_session_cookie
from app.routers.web.views import templates

router = APIRouter(tags=["survey experience"])


def page(request, name, **context):
    response = templates.TemplateResponse(request=request, name=name, context=context)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@router.get("/survey/login")
def login_page(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME, "")
    session = admin_session.find_session(db, token)
    if not session or session.user_id:
        try:
            require_respondent(request, db)
            return RedirectResponse("/survey", status_code=303)
        except HTTPException:
            pass
        admin_session.delete_session(db, token)
        token = admin_session.create_session(db)
    response = page(request, "survey/login.html", csrf_token=csrf_token(token))
    set_session_cookie(response, token)
    return response


@router.post("/survey/login")
async def login(request: Request, db: Session = Depends(get_db)):
    fields = await read_form(request, db)
    account = await run_in_threadpool(
        user.authenticate_account,
        db,
        fields.get("username", ""),
        fields.get("password", ""),
    )
    token = request.cookies[COOKIE_NAME]
    if not account:
        response = page(
            request,
            "survey/login.html",
            csrf_token=csrf_token(token),
            error="The username or password is incorrect.",
            username=fields.get("username", ""),
        )
        response.status_code = 401
        return response
    account_id = account.id
    from app.services.forms import audit

    audit(db, account_id, "auth.login", "user", account_id)
    admin_session.delete_session(db, token)
    token = admin_session.create_session(db, account_id)
    response = RedirectResponse("/survey", status_code=303)
    response.headers["Cache-Control"] = "no-store"
    set_session_cookie(response, token, authenticated=True)
    return response


@router.get("/api/session")
def session(account=Depends(require_respondent)):
    return JSONResponse(
        {"id": account.id, "username": account.username},
        headers={"Cache-Control": "no-store"},
    )


@router.get("/survey")
@router.get("/survey/forms/{form_id}")
def survey_page(
    request: Request, form_id: int | None = None, db: Session = Depends(get_db)
):
    try:
        account = require_respondent(request, db)
    except HTTPException:
        return RedirectResponse(
            "/survey/login", status_code=303, headers={"Cache-Control": "no-store"}
        )
    token = request.cookies[COOKIE_NAME]
    return page(
        request,
        "survey/form.html",
        username=account.username,
        form_id=form_id,
        csrf_token=csrf_token(token),
    )

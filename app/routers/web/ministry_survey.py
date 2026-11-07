"""Public ministry survey: year selection, grouped questions and submission."""
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import settings
from app.crud import ministry_survey as survey_crud
from app.dependencies import get_survey_connection
from app.routers.web.views import templates
from app.services.survey_formatting import year_view as _year_view

router = APIRouter(tags=["ministry survey"])

CSRF_COOKIE = "dedc_ministry_survey"
CSRF_MAX_AGE = 60 * 60 * 8
MAX_ITEM_COUNT = 2_147_483_647
MAX_DESCRIPTION_LENGTH = 4_000
UNGROUPED_KEY = "other"


def _page(request, name, context, status_code=200):
    response = templates.TemplateResponse(
        request=request,
        name=name,
        context=context,
        status_code=status_code,
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    return response


def _question_groups(questions):
    groups = {}
    number = 0
    for question in questions:
        number += 1
        key = (
            question["qTID"]
            if question["qTID"] is not None
            else UNGROUPED_KEY
        )
        group = groups.get(key)
        if group is None:
            group = {
                "key": key,
                "anchor": f"group-{key}",
                "title": question["qTDetail"] or "အခြား မေးခွန်းများ",
                "description": question["titleDescription"] or "",
                "questions": [],
            }
            groups[key] = group
        group["questions"].append({**question, "number": number})
    return list(groups.values())


def _csrf_value(request):
    existing = request.cookies.get(CSRF_COOKIE, "")
    if existing and len(existing) >= 20:
        return existing, False
    return secrets.token_urlsafe(32), True


def _form_values(form, questions):
    values = {}
    for question in questions:
        question_id = question["mQId"]
        values[question_id] = {
            "has": str(form.get(f"has_{question_id}") or ""),
            "count": str(form.get(f"count_{question_id}") or ""),
            "description": str(
                form.get(f"description_{question_id}") or ""
            ),
        }
    return values


def _validate_submission(form, questions, ministries_by_id):
    errors = []
    errors_by_question = {}

    raw_ministry = str(form.get("ministryId") or "").strip()
    try:
        ministry_id = int(raw_ministry)
    except (TypeError, ValueError):
        ministry_id = None
    if ministry_id is None or ministry_id not in ministries_by_id:
        errors.append("ဝန်ကြီးဌာနကို စာရင်းမှ ရွေးချယ်ပါ။")

    answers = {}
    for question_number, question in enumerate(questions, start=1):
        question_id = question["mQId"]
        question_errors = []
        raw_has = str(form.get(f"has_{question_id}") or "").strip()
        has_item = raw_has == "1"
        item_count = None
        survey_description = None

        if raw_has not in ("0", "1"):
            question_errors.append("ရှိ/မရှိ ကို ရွေးချယ်ပါ။")
        elif has_item:
            raw_count = str(
                form.get(f"count_{question_id}") or ""
            ).strip()
            try:
                item_count = int(raw_count)
            except (TypeError, ValueError):
                item_count = None
            if item_count is None or item_count < 0:
                question_errors.append(
                    "အရေအတွက်ကို မှန်ကန်သော ကိန်းဂဏန်းဖြင့် ဖြည့်ပါ။"
                )
            elif item_count > MAX_ITEM_COUNT:
                question_errors.append(
                    "အရေအတွက် ပမာဏ များလွန်းနေပါသည်။"
                )

            survey_description = str(
                form.get(f"description_{question_id}") or ""
            ).strip()
            if not survey_description:
                question_errors.append("အကြောင်းအရာကို ဖြည့်ပါ။")
            elif len(survey_description) > MAX_DESCRIPTION_LENGTH:
                question_errors.append(
                    "အကြောင်းအရာသည် စာလုံး "
                    f"{MAX_DESCRIPTION_LENGTH} လုံးထက် မကျော်ရပါ။"
                )

        answers[question_id] = {
            "has_item": has_item,
            "item_count": item_count if has_item else None,
            "survey_description": (
                survey_description if has_item else None
            ),
        }
        if question_errors:
            errors_by_question[question_id] = question_errors
            errors.append(
                f"မေးခွန်း {question_number}: {question_errors[0]}"
            )

    return ministry_id, answers, errors, errors_by_question


def _render_form(
    request,
    year,
    questions,
    ministries,
    values=None,
    selected_ministry_id=None,
    errors=None,
    errors_by_question=None,
    csrf_token=None,
    set_csrf_cookie=False,
    status_code=200,
    submitted_status=None,
    saved=0,
    skipped=0,
):
    values = values or {}
    errors = errors or []
    errors_by_question = errors_by_question or {}
    if csrf_token is None:
        csrf_token, set_csrf_cookie = _csrf_value(request)

    selected_ministry = next(
        (
            ministry
            for ministry in ministries
            if ministry["ministryId"] == selected_ministry_id
        ),
        None,
    )
    identity_error = any(
        "စာရင်းမှ ရွေးချယ်ပါ" in error for error in errors
    )
    response = _page(
        request,
        "survey/ministry_form.html",
        {
            "year": _year_view(year),
            "groups": _question_groups(questions),
            "question_count": len(questions),
            "ministries": ministries,
            "selected_ministry": selected_ministry,
            "identity_error": identity_error,
            "values": values,
            "errors": errors,
            "errors_by_question": errors_by_question,
            "csrf_token": csrf_token,
            "submitted_status": submitted_status,
            "saved": saved,
            "skipped": skipped,
        },
        status_code=status_code,
    )
    if set_csrf_cookie:
        response.set_cookie(
            CSRF_COOKIE,
            csrf_token,
            max_age=CSRF_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=settings.PORTAL_COOKIE_SECURE,
            path="/surveys/ministry",
        )
    return response


@router.get("/surveys/ministry", response_class=HTMLResponse)
def ministry_years(
    request: Request, connection=Depends(get_survey_connection)
):
    years = [
        _year_view(year) for year in survey_crud.active_years(connection)
    ]
    return _page(
        request,
        "survey/ministry_years.html",
        {
            "years": years,
            "unavailable": request.query_params.get("unavailable") == "1",
        },
    )


@router.get("/surveys/ministry/{year_id}", response_class=HTMLResponse)
def ministry_survey_form(
    request: Request,
    year_id: int,
    connection=Depends(get_survey_connection),
):
    year = survey_crud.active_year(connection, year_id)
    if not year:
        return RedirectResponse(
            "/surveys/ministry?unavailable=1", status_code=303
        )

    questions = survey_crud.questions_for_year(connection, year_id)
    if not questions:
        return RedirectResponse(
            "/surveys/ministry?unavailable=1", status_code=303
        )

    submitted_status = request.query_params.get("status")
    saved = _query_int(request.query_params.get("saved"))
    skipped = _query_int(request.query_params.get("skipped"))
    return _render_form(
        request,
        year,
        questions,
        survey_crud.ministries(connection),
        submitted_status=submitted_status,
        saved=saved,
        skipped=skipped,
    )


@router.post("/surveys/ministry/{year_id}", response_class=HTMLResponse)
async def submit_ministry_survey(
    request: Request,
    year_id: int,
    connection=Depends(get_survey_connection),
):
    year = survey_crud.active_year(connection, year_id)
    if not year:
        return RedirectResponse(
            "/surveys/ministry?unavailable=1", status_code=303
        )

    questions = survey_crud.questions_for_year(connection, year_id)
    if not questions:
        return RedirectResponse(
            "/surveys/ministry?unavailable=1", status_code=303
        )

    ministries = survey_crud.ministries(connection)
    form = await request.form()
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    form_token = str(form.get("csrf_token") or "")
    if (
        not cookie_token
        or not form_token
        or not secrets.compare_digest(cookie_token, form_token)
    ):
        values = _form_values(form, questions)
        return _render_form(
            request,
            year,
            questions,
            ministries,
            values=values,
            errors=[
                "ဖောင်၏ သက်တမ်းကုန်ဆုံးသွားပါသည်။ ထပ်မံကြိုးစားပါ။"
            ],
            csrf_token=secrets.token_urlsafe(32),
            set_csrf_cookie=True,
            status_code=400,
        )

    ministries_by_id = {
        ministry["ministryId"]: ministry for ministry in ministries
    }
    ministry_id, answers, errors, errors_by_question = (
        _validate_submission(form, questions, ministries_by_id)
    )
    if errors:
        return _render_form(
            request,
            year,
            questions,
            ministries,
            values=_form_values(form, questions),
            selected_ministry_id=ministry_id,
            errors=errors,
            errors_by_question=errors_by_question,
            status_code=400,
        )

    saved, skipped = survey_crud.save_answers(
        connection, ministry_id, questions, answers
    )
    if saved and skipped:
        status = "partial"
    elif saved:
        status = "saved"
    else:
        status = "already"
    query = urlencode(
        {"status": status, "saved": saved, "skipped": skipped}
    )
    return RedirectResponse(
        f"/surveys/ministry/{year_id}?{query}", status_code=303
    )


def _query_int(value):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0

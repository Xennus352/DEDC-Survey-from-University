"""Real admin screens share one authenticated shell and API client."""

from fastapi import APIRouter, Depends, Request
from app.admin_auth import COOKIE_NAME, AdminIdentity, require_admin
from app.routers.web.portal import render

router = APIRouter(
    prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(require_admin)]
)
PAGES = {
    "forms": "စစ်တမ်းများ",
    "departments": "တက္ကသိုလ်များ",
    "ministries": "ဝန်ကြီးဌာနများ",
    "reports": "တက္ကသိုလ် အစီရင်ခံစာများ",
    "settings": "ဆက်တင်များ",
}


@router.get("/forms/{form_id}", name="form_editor")
def editor(
    form_id: int, request: Request, admin: AdminIdentity = Depends(require_admin)
):
    return render(
        request,
        "dashboard",
        request.cookies[COOKIE_NAME],
        username=admin.username,
        page="editor",
        page_title="Form builder",
        form_id=form_id,
    )


@router.get("/forms/{form_id}/preview", name="form_preview")
def preview(
    form_id: int, request: Request, admin: AdminIdentity = Depends(require_admin)
):
    return render(
        request,
        "dashboard",
        request.cookies[COOKIE_NAME],
        username=admin.username,
        page="preview",
        page_title="Form preview",
        form_id=form_id,
    )


@router.get("/reports/university-answers", name="university_answers")
def university_answers(
    request: Request, admin: AdminIdentity = Depends(require_admin)
):
    return render(
        request,
        "dashboard",
        request.cookies[COOKIE_NAME],
        username=admin.username,
        active_tab="years",
        page="university_answers",
        page_title="တက္ကသိုလ် အဖြေများ",
    )


@router.get(
    "/reports/question-answer-rates", name="question_answer_rates"
)
def question_answer_rates(
    request: Request, admin: AdminIdentity = Depends(require_admin)
):
    return render(
        request,
        "dashboard",
        request.cookies[COOKIE_NAME],
        username=admin.username,
        active_tab="years",
        page="question_answer_rates",
        page_title="မေးခွန်း ဖြေဆိုနှုန်းများ",
    )


@router.get("/reports/ministry", name="ministry_reports")
def ministry_reports(
    request: Request, admin: AdminIdentity = Depends(require_admin)
):
    return render(
        request,
        "dashboard",
        request.cookies[COOKIE_NAME],
        username=admin.username,
        active_tab="years",
        page="ministry_reports",
        page_title="ဝန်ကြီးဌာန အစီရင်ခံစာများ",
    )


@router.get("/reports/ministry-answers", name="ministry_answers")
def ministry_answers(
    request: Request, admin: AdminIdentity = Depends(require_admin)
):
    return render(
        request,
        "dashboard",
        request.cookies[COOKIE_NAME],
        username=admin.username,
        active_tab="years",
        page="ministry_answers",
        page_title="ဝန်ကြီးဌာန အဖြေများ",
    )


@router.get(
    "/reports/ministry-question-answer-rates",
    name="ministry_question_answer_rates",
)
def ministry_question_answer_rates(
    request: Request, admin: AdminIdentity = Depends(require_admin)
):
    return render(
        request,
        "dashboard",
        request.cookies[COOKIE_NAME],
        username=admin.username,
        active_tab="years",
        page="ministry_question_answer_rates",
        page_title="ဝန်ကြီးဌာန မေးခွန်း ဖြေဆိုနှုန်းများ",
    )


@router.get("/{page}", name="dashboard_page")
def page(page: str, request: Request, admin: AdminIdentity = Depends(require_admin)):
    from fastapi import HTTPException

    if page not in PAGES:
        raise HTTPException(404, "Page not found.")
    return render(
        request,
        "dashboard",
        request.cookies[COOKIE_NAME],
        username=admin.username,
        active_tab="years",
        page=page,
        page_title=PAGES[page],
    )

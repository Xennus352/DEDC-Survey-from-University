
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter(tags=["web"])

BASE_DIR = Path(__file__).resolve().parents[3]

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )


@router.get("/roadmap", response_class=HTMLResponse)
async def roadmap(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="RoadMap.html"
    )


@router.get("/RoadMap.html", include_in_schema=False)
async def roadmap_legacy():
    return RedirectResponse(url="/roadmap", status_code=301)

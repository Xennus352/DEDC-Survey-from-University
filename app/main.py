from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.admin_auth import AdminAuthorizationMiddleware
from app.middleware import BodySizeLimitMiddleware, StaticCacheMiddleware
from app.routers import admin, forms
from app.routers.web import dashboard, portal, survey, views

app = FastAPI(title="DEDC Survey API")
app.add_middleware(AdminAuthorizationMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(StaticCacheMiddleware)

BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(views.router)
app.include_router(portal.router)
app.include_router(dashboard.router)
app.include_router(survey.router)
app.include_router(admin.router)
app.include_router(forms.router)
app.include_router(forms.files_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


@app.exception_handler(IntegrityError)
async def constraint_conflict(request: Request, error: IntegrityError):
    return JSONResponse(
        {
            "detail": "This change conflicts with an existing or protected record. Reload and try again."
        },
        status_code=409,
        headers={"Cache-Control": "no-store"},
    )

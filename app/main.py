from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.routers import surveys, questions, responses
from app.routers.web import portal, views

app = FastAPI(title="DEDC Survey API")

BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(surveys.router)
app.include_router(questions.router)
app.include_router(responses.router)
app.include_router(views.router)
app.include_router(portal.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

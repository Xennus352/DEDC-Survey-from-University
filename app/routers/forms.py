"""Additive published-schema API; existing mobile API payloads are unchanged."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models.forms import SurveyForm
from app.services.forms import published_version, version_payload

router = APIRouter(prefix="/api/forms", tags=["published forms"])


@router.get("")
def available_forms(db: Session = Depends(get_db)):
    return [
        {"id": f.id, "title": f.title, "audience": f.audience}
        for f in db.query(SurveyForm).filter_by(archived=False).all()
        if any(v.status == "published" for v in f.versions)
    ]


@router.get("/{form_id}/schema")
def schema(form_id: int, db: Session = Depends(get_db)):
    return version_payload(published_version(db, form_id))


from fastapi import Request
from app.admin_auth import require_survey_csrf
from app.schemas.forms import SubmissionInput
from app.services.forms import submit


@router.post("/{form_id}/submissions", status_code=201)
def create_submission(
    form_id: int,
    data: SubmissionInput,
    account=Depends(require_survey_csrf),
    db: Session = Depends(get_db),
):
    row = submit(db, form_id, data, account.id)
    return {"id": row.id, "version_id": row.version_id, "status": row.status}


from fastapi import File, Form, UploadFile
from fastapi.responses import Response
from urllib.parse import quote
from app.admin_auth import require_respondent
from app.models.forms import AnswerFile
from app.crud.user import find_admin


@router.post("/{form_id}/files", status_code=201)
def upload_answer_file(
    form_id: int,
    key: str = Form(...),
    file: UploadFile = File(...),
    account=Depends(require_survey_csrf),
    db: Session = Depends(get_db),
):
    from app.services.files import MAX_FILE, upload

    return upload(
        db,
        published_version(db, form_id),
        key,
        file.filename,
        file.file.read(MAX_FILE + 1),
        account.id,
    )


files_router = APIRouter(prefix="/api/files", tags=["answer files"])


@files_router.get("/{file_id}")
def download_file(
    file_id: int, account=Depends(require_respondent), db: Session = Depends(get_db)
):
    record = db.get(AnswerFile, file_id)
    if not record or record.user_id != account.id and not find_admin(db, account.id):
        raise HTTPException(404, "File not found.")
    return Response(
        record.content,
        media_type="application/octet-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "attachment; filename*=UTF-8''"
            + quote(record.filename),
        },
    )

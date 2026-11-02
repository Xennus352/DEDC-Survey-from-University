"""Protected administrator endpoints; existing mobile endpoints stay compatible."""

from fastapi import APIRouter, Depends

from app.admin_auth import AdminIdentity, require_admin

router = APIRouter(prefix="/api/admin", tags=["administration"])


@router.get("/session")
def session_status(admin: AdminIdentity = Depends(require_admin)):
    return {"id": admin.id, "username": admin.username, "role_id": admin.role_id}


from datetime import date, datetime, timezone
from io import BytesIO, StringIO
import csv
import json
from fastapi import File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models.forms import (
    AuditLog,
    FormField,
    FormVersion,
    Submission,
    SurveyForm,
    WorkbookAnswer,
    WorkbookImport,
)
from app.models.user import User, UserRole
from app.portal_auth import hash_password
from app.schemas.forms import CreateForm, DraftInput, SubmissionInput, PreviewInput
from app.services import forms, reports, workbook
from pydantic import BaseModel, Field, ValidationError


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    return reports.overview(db)


@router.get("/forms")
def list_forms(
    search: str = "",
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(SurveyForm)
    if search:
        query = query.filter(SurveyForm.title.contains(search))
    total = query.count()
    rows = (
        query.order_by(SurveyForm.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "id": f.id,
                "title": f.title,
                "audience": f.audience,
                "archived": f.archived,
                "versions": [
                    {
                        "id": v.id,
                        "number": v.number,
                        "status": v.status,
                        "fields": sum(len(s.questions) for s in v.sections),
                    }
                    for v in f.versions
                ],
            }
            for f in rows
        ],
    }


@router.post("/forms", status_code=201)
def create_form(
    data: CreateForm,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return forms.form_payload(forms.create_form(db, data, admin.id))


@router.get("/forms/{form_id}")
def read_form(form_id: int, db: Session = Depends(get_db)):
    return forms.form_payload(forms.get_form(db, form_id))


@router.put("/forms/{form_id}/versions/{version_id}")
def save_form(
    form_id: int,
    version_id: int,
    data: DraftInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return forms.version_payload(
        forms.save_draft(db, form_id, version_id, data, admin.id)
    )


@router.post("/forms/{form_id}/versions", status_code=201)
def new_version(
    form_id: int,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return forms.version_payload(forms.clone_version(db, form_id, admin.id))


class PublishInput(BaseModel):
    revision: int = Field(ge=1)


@router.post("/forms/{form_id}/versions/{version_id}/publish")
def publish_form(
    form_id: int,
    version_id: int,
    data: PublishInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return forms.version_payload(
        forms.publish(db, form_id, version_id, data.revision, admin.id)
    )


@router.post("/forms/{form_id}/duplicate", status_code=201)
def duplicate_form(
    form_id: int,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return forms.form_payload(forms.duplicate(db, form_id, admin.id))


class ArchiveInput(BaseModel):
    archived: bool


@router.post("/forms/{form_id}/archive")
def archive_form(
    form_id: int,
    data: ArchiveInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    form = forms.get_form(db, form_id, True)
    form.archived = data.archived
    forms.audit(
        db,
        admin.id,
        "form.archive" if data.archived else "form.restore",
        "form",
        form.id,
    )
    db.commit()
    return {"id": form.id, "archived": form.archived}


@router.delete("/forms/{form_id}", status_code=204)
def delete_form(
    form_id: int,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    forms.delete_draft_form(db, form_id, admin.id)


@router.post("/imports/preview")
def preview_import(file: UploadFile = File(...)):
    return workbook.parse_workbook(file.file.read(workbook.MAX_UPLOAD + 1))


@router.post("/imports/confirm", status_code=201)
def confirm_import(
    file: UploadFile = File(...),
    worksheet: str = Form(...),
    definition: str = Form(...),
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    content = file.file.read(workbook.MAX_UPLOAD + 1)
    preview = workbook.parse_workbook(content)
    from app.services.workbook_export import archive_template

    archive_template(db, content, file.filename or "DEDC Survey.xlsx")
    try:
        data = DraftInput.model_validate_json(definition)
    except ValidationError as error:
        raise HTTPException(422, str(error))
    return forms.form_payload(
        workbook.import_sheet(db, preview, worksheet, data, admin.id)
    )


@router.get("/source-answers")
def source_answers(
    search: str = "",
    import_id: int | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(WorkbookAnswer).join(WorkbookImport)
    if search:
        query = query.filter(WorkbookAnswer.question.contains(search))
    if import_id:
        query = query.filter(WorkbookAnswer.import_id == import_id)
    total = query.count()
    imports = db.query(WorkbookImport).order_by(WorkbookImport.id.desc()).all()
    items = []
    for row in (
        query.order_by(WorkbookAnswer.id).offset((page - 1) * limit).limit(limit)
    ):
        source = db.get(WorkbookImport, row.import_id)
        items.append(
            {
                "id": row.id,
                "worksheet": source.worksheet,
                "number": row.number,
                "question": row.question,
                "source_cell": row.source_cell,
                "present": row.present_text,
                "absent": row.absent_text,
                "quantity": row.quantity_text,
                "details": row.details_text,
            }
        )
    return {
        "total": total,
        "items": items,
        "imports": [
            {"id": i.id, "worksheet": i.worksheet, "version_id": i.version_id}
            for i in imports
        ],
    }


@router.get("/questions")
def question_bank(
    search: str = "",
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(FormField).join(FormVersion)
    if search:
        query = query.filter(
            FormField.title.contains(search) | FormField.key.contains(search)
        )
    total = query.count()
    items = []
    for q in (
        query.order_by(FormField.id.desc()).offset((page - 1) * limit).limit(limit)
    ):
        v = db.get(FormVersion, q.version_id)
        items.append(
            {
                "key": q.key,
                "title": q.title,
                "kind": q.kind,
                "required": q.required,
                "form_id": v.form_id,
                "form": v.title,
                "version": v.number,
                "status": v.status,
            }
        )
    return {"total": total, "items": items}


@router.get("/submissions")
@router.get("/reports")
def list_submissions(
    search: str = "",
    form_id: int | None = None,
    version_id: int | None = None,
    status: str | None = None,
    user_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    question: str | None = None,
    operator: str = "equals",
    answer: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if operator not in {"equals", "contains", "greater_than", "less_than"}:
        raise HTTPException(422, "Unsupported answer filter.")
    try:
        query = reports.filtered_submissions(
            db,
            search,
            form_id,
            version_id,
            status,
            user_id,
            start,
            end,
            question,
            operator,
            answer,
        )
    except ValueError:
        raise HTTPException(422, "Numeric filters need a numeric answer.")
    total = query.count()
    statuses = dict(
        query.with_entities(Submission.status, func.count())
        .group_by(Submission.status)
        .all()
    )
    return {
        "total": total,
        "statuses": statuses,
        "analytics": reports.analytics(db, query, question),
        "items": [
            reports.submission_row(db, row)
            for row in query.order_by(Submission.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ],
    }


@router.get("/submissions/{submission_id}")
def submission_detail(submission_id: int, db: Session = Depends(get_db)):
    row = db.get(Submission, submission_id)
    if not row:
        raise HTTPException(404, "Submission not found.")
    return reports.submission_detail(db, row)


class ReviewInput(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)
    status: str


@router.post("/submissions/review")
def review_submissions(
    data: ReviewInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if data.status not in {"pending_review", "approved", "rejected"}:
        raise HTTPException(422, "Invalid review status.")
    rows = db.query(Submission).filter(Submission.id.in_(data.ids)).all()
    if len(rows) != len(set(data.ids)):
        raise HTTPException(404, "One or more submissions were not found.")
    for row in rows:
        before = row.status
        row.status = data.status
        forms.audit(
            db,
            admin.id,
            "submission.review",
            "submission",
            row.id,
            before=before,
            after=data.status,
        )
    db.commit()
    return {"updated": len(rows)}


def safe_cell(value):
    # Prevent spreadsheet formula execution when exporting user-controlled text.
    value = str(value) if value is not None else ""
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


@router.get("/reports/export/{format}")
def export_reports(
    format: str,
    request: Request,
    search: str = "",
    form_id: int | None = None,
    version_id: int | None = None,
    status: str | None = None,
    user_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    question: str | None = None,
    operator: str = "equals",
    answer: str | None = None,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if format not in {"csv", "xlsx", "pdf"}:
        raise HTTPException(422, "Choose CSV, XLSX or PDF.")
    if operator not in {"equals", "contains", "greater_than", "less_than"}:
        raise HTTPException(422, "Unsupported answer filter.")
    try:
        query = reports.filtered_submissions(
            db,
            search,
            form_id,
            version_id,
            status,
            user_id,
            start,
            end,
            question,
            operator,
            answer,
        )
    except ValueError:
        raise HTTPException(422, "Numeric filters need a numeric answer.")
    if query.count() > 10000:
        raise HTTPException(422, "Narrow the filters to at most 10,000 submissions.")
    rows = [
        ["DEDC survey report"],
        ["Exported at", datetime.now(timezone.utc).isoformat()],
        ["Filters", json.dumps(dict(request.query_params), ensure_ascii=False)],
        ["Submissions", query.count()],
        [],
        [
            "Submission",
            "Form",
            "Version",
            "Status",
            "User",
            "Created at",
            "Reporting from",
            "Reporting to",
            "Section",
            "Question key",
            "Question",
            "Answer",
        ],
    ]
    for item in query.order_by(Submission.id):
        detail = reports.submission_detail(db, item)
        for section in detail["sections"]:
            for a in section["answers"]:
                rows.append(
                    [
                        detail["id"],
                        detail["form"],
                        detail["version"],
                        detail["status"],
                        detail["username"],
                        detail["created_at"],
                        detail["reporting_start"],
                        detail["reporting_end"],
                        section["title"],
                        a["key"],
                        a["title"],
                        json.dumps(a["value"], ensure_ascii=False)
                        if isinstance(a["value"], (dict, list))
                        else str(a["value"])
                        if a["value"] is not None
                        else "",
                    ]
                )
    rows = [[safe_cell(cell) for cell in row] for row in rows]
    if format == "pdf":
        from app.services.exports import pdf_document

        content = pdf_document(
            rows,
            "DEDC Survey Report"
            if "Submissions" in str(rows[:4])
            else "DEDC Original Workbook Answers",
        )
        media = "application/pdf"
    elif format == "csv":
        stream = StringIO()
        csv.writer(stream).writerows(rows)
        content = ("\ufeff" + stream.getvalue()).encode("utf-8")
        media = "text/csv; charset=utf-8"
    else:
        from openpyxl import Workbook

        book = Workbook()
        sheet = book.active
        sheet.title = "Survey report"
        for row in rows:
            sheet.append(row)
        stream = BytesIO()
        book.save(stream)
        content = stream.getvalue()
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    forms.audit(
        db,
        admin.id,
        "report.export",
        "report",
        None,
        format=format,
        filters=dict(request.query_params),
    )
    db.commit()
    return Response(
        content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="dedc-report.{format}"'},
    )


class UserInput(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    role_id: int
    is_active: bool = True
    password: str | None = Field(default=None, min_length=8, max_length=1024)


@router.get("/users")
def users(
    search: str = "",
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if search:
        query = query.filter(User.username.contains(search))
    return {
        "total": query.count(),
        "roles": [{"id": r.id, "name": r.name} for r in db.query(UserRole).all()],
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "role_id": u.role_id,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
            }
            for u in query.order_by(User.id).offset((page - 1) * limit).limit(limit)
        ],
    }


@router.post("/users", status_code=201)
def add_user(
    data: UserInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not data.password:
        raise HTTPException(422, "A password is required for new accounts.")
    if not db.get(UserRole, data.role_id):
        raise HTTPException(422, "Role not found.")
    if db.query(User).filter_by(username=data.username).first():
        raise HTTPException(409, "Username already exists.")
    account = User(
        username=data.username,
        role_id=data.role_id,
        is_active=data.is_active,
        password_hash=hash_password(data.password),
    )
    db.add(account)
    db.flush()
    forms.audit(
        db,
        admin.id,
        "user.create",
        "user",
        account.id,
        username=data.username,
        role_id=data.role_id,
    )
    db.commit()
    return {"id": account.id}


@router.put("/users/{user_id}")
def edit_user(
    user_id: int,
    data: UserInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.config import settings

    account = db.query(User).filter_by(id=user_id).with_for_update().first()
    if not account:
        raise HTTPException(404, "User not found.")
    role = db.get(UserRole, data.role_id)
    if not role:
        raise HTTPException(422, "Role not found.")
    if account.id == admin.id and (
        not data.is_active or role.name != settings.ADMIN_ROLE_NAME
    ):
        raise HTTPException(409, "You cannot remove your own administrator access.")
    if (
        db.query(User)
        .filter(User.username == data.username, User.id != user_id)
        .first()
    ):
        raise HTTPException(409, "Username already exists.")
    account.username = data.username
    account.role_id = data.role_id
    account.is_active = data.is_active
    if data.password:
        account.password_hash = hash_password(data.password)
    forms.audit(
        db,
        admin.id,
        "user.edit",
        "user",
        user_id,
        username=data.username,
        role_id=data.role_id,
        is_active=data.is_active,
    )
    db.commit()
    return {"id": account.id}


@router.get("/audit")
def audit_logs(
    search: str = "",
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if search:
        query = query.filter(
            AuditLog.action.contains(search) | AuditLog.entity.contains(search)
        )
    return {
        "total": query.count(),
        "items": [
            {
                "id": a.id,
                "actor_id": a.actor_id,
                "action": a.action,
                "entity": a.entity,
                "target_id": a.target_id,
                "changes": a.changes,
                "created_at": a.created_at.isoformat(),
            }
            for a in query.order_by(AuditLog.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ],
    }


@router.post("/forms/{form_id}/submit", status_code=201)
def submit_form(
    form_id: int,
    data: SubmissionInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = forms.submit(db, form_id, data, admin.id)
    return {"id": row.id, "version_id": row.version_id}


@router.post("/forms/{form_id}/versions/{version_id}/validate")
def validate_preview(
    form_id: int,
    version_id: int,
    data: PreviewInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.services.form_logic import validate_answers
    from app.services.files import owned_files

    version = forms.get_version(db, form_id, version_id)
    clean = validate_answers(version, data.answers)
    owned_files(db, version, clean, admin.id)
    return {"valid": True, "answers": clean}


@router.get("/source-answers/export/{format}")
def export_source(
    format: str,
    request: Request,
    search: str = "",
    import_id: int | None = None,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if format not in {"csv", "xlsx", "pdf"}:
        raise HTTPException(422, "Choose CSV, XLSX or PDF.")
    query = db.query(WorkbookAnswer).join(WorkbookImport)
    if search:
        query = query.filter(WorkbookAnswer.question.contains(search))
    if import_id:
        query = query.filter(WorkbookAnswer.import_id == import_id)
    if query.count() > 10000:
        raise HTTPException(422, "Narrow the selection to at most 10,000 source rows.")
    rows = [
        ["DEDC original workbook answers"],
        ["Exported at", datetime.now(timezone.utc).isoformat()],
        ["Filters", json.dumps(dict(request.query_params), ensure_ascii=False)],
        [],
        [
            "Worksheet",
            "Number",
            "Question",
            "Cell",
            "Present",
            "Absent",
            "Quantity",
            "Details",
        ],
    ]
    for r in query.order_by(WorkbookAnswer.id):
        rows.append(
            [
                db.get(WorkbookImport, r.import_id).worksheet,
                r.number,
                r.question,
                r.source_cell,
                r.present_text,
                r.absent_text,
                r.quantity_text,
                r.details_text,
            ]
        )
    rows = [[safe_cell(cell) for cell in row] for row in rows]
    if format == "pdf":
        from app.services.exports import pdf_document

        content = pdf_document(
            rows,
            "DEDC Survey Report"
            if "Submissions" in str(rows[:4])
            else "DEDC Original Workbook Answers",
        )
        media = "application/pdf"
    elif format == "csv":
        stream = StringIO()
        csv.writer(stream).writerows(rows)
        content = ("\ufeff" + stream.getvalue()).encode()
        media = "text/csv; charset=utf-8"
    else:
        from openpyxl import Workbook

        book = Workbook()
        sheet = book.active
        sheet.title = "Original answers"
        for row in rows:
            sheet.append(row)
        stream = BytesIO()
        book.save(stream)
        content = stream.getvalue()
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    forms.audit(
        db,
        admin.id,
        "source.export",
        "workbook",
        import_id,
        format=format,
        filters=dict(request.query_params),
    )
    db.commit()
    return Response(
        content,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="dedc-source-answers.{format}"'
        },
    )


@router.post("/forms/{form_id}/versions/{version_id}/files", status_code=201)
def upload_preview_file(
    form_id: int,
    version_id: int,
    key: str = Form(...),
    file: UploadFile = File(...),
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.services.files import MAX_FILE, upload

    return upload(
        db,
        forms.get_version(db, form_id, version_id),
        key,
        file.filename,
        file.file.read(MAX_FILE + 1),
        admin.id,
    )


@router.get("/search")
def global_search(
    q: str = Query(..., min_length=2, max_length=100), db: Session = Depends(get_db)
):
    results = []
    for f in db.query(SurveyForm).filter(SurveyForm.title.contains(q)).limit(8):
        results.append(
            {"title": f.title, "type": "Form", "url": f"/dashboard/forms/{f.id}"}
        )
    for field in (
        db.query(FormField)
        .filter(FormField.title.contains(q) | FormField.key.contains(q))
        .limit(8)
    ):
        version = db.get(FormVersion, field.version_id)
        results.append(
            {
                "title": field.title,
                "type": "Question",
                "url": f"/dashboard/forms/{version.form_id}?version={version.id}",
            }
        )
    for account in db.query(User).filter(User.username.contains(q)).limit(5):
        results.append(
            {
                "title": account.username,
                "type": "User",
                "url": f"/dashboard/users?search={account.username}",
            }
        )
    return {"items": results}


@router.get("/users/export/{format}")
def export_users(
    format: str,
    search: str = "",
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if format not in {"csv", "xlsx", "pdf"}:
        raise HTTPException(422, "Choose CSV, XLSX or PDF.")
    query = db.query(User)
    if search:
        query = query.filter(User.username.contains(search))
    if query.count() > 10000:
        raise HTTPException(422, "Narrow the search to at most 10,000 users.")
    rows = [
        ["DEDC User Directory"],
        ["Exported at", datetime.now(timezone.utc).isoformat()],
        ["Search", search],
        [],
        ["User ID", "Username", "Role", "Active", "Created at"],
    ]
    for user in query.order_by(User.id):
        role = db.get(UserRole, user.role_id)
        rows.append(
            [
                user.id,
                user.username,
                role.name if role else "",
                user.is_active,
                user.created_at.isoformat(),
            ]
        )
    rows = [[safe_cell(cell) for cell in row] for row in rows]
    if format == "pdf":
        from app.services.exports import pdf_document

        content = pdf_document(rows, "DEDC User Directory")
        media = "application/pdf"
    elif format == "csv":
        stream = StringIO()
        csv.writer(stream).writerows(rows)
        content = ("\ufeff" + stream.getvalue()).encode()
        media = "text/csv; charset=utf-8"
    else:
        from openpyxl import Workbook

        book = Workbook()
        sheet = book.active
        sheet.title = "Users"
        for row in rows:
            sheet.append(row)
        stream = BytesIO()
        book.save(stream)
        content = stream.getvalue()
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    forms.audit(
        db, admin.id, "users.export", "user", None, format=format, search=search
    )
    db.commit()
    return Response(
        content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="dedc-users.{format}"'},
    )


@router.get("/forms/{form_id}/export/excel")
def export_form_excel(
    form_id: int,
    version_id: int | None = None,
    answers: bool = False,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.services.workbook_export import export_form

    content = export_form(db, form_id, version_id, answers)
    forms.audit(
        db,
        admin.id,
        "form.excel_export",
        "form",
        form_id,
        version_id=version_id,
        answers=answers,
    )
    db.commit()
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="dedc-form-{form_id}-'
            + ("questions-and-answers" if answers else "questions-only")
            + '.xlsx"'
        },
    )


@router.get("/workbook/export/excel")
def export_original_excel(
    answers: bool = False,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.services.workbook_export import original_workbook

    content = original_workbook(db, answers)
    forms.audit(
        db, admin.id, "workbook.excel_export", "workbook", None, answers=answers
    )
    db.commit()
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="dedc-original-'
            + ("questions-and-answers" if answers else "questions-only")
            + '.xlsx"'
        },
    )


class RoleInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)


@router.post("/roles", status_code=201)
def create_role(
    data: RoleInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    name = data.name.strip()
    if not name:
        raise HTTPException(422, "Enter a role name.")
    if db.query(UserRole).filter_by(name=name).first():
        raise HTTPException(409, "Role already exists.")
    role = UserRole(name=name)
    db.add(role)
    db.flush()
    forms.audit(db, admin.id, "role.create", "role", role.id, name=name)
    db.commit()
    return {"id": role.id, "name": role.name}

"""Protected endpoints for the current administration workspace."""

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session

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
from sqlalchemy import func, select, literal, union_all
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
from app.storage.schema import metadata as persistent_metadata
from app.models.user import User, UserRole
from app.portal_auth import hash_password, verify_password
from app.schemas.forms import CreateForm, DraftInput, SubmissionInput, PreviewInput, QuestionInput
from app.services import forms, reports, university_reports, workbook
from app.services.presentation import audit_action, label
from pydantic import BaseModel, Field, ValidationError


@router.get("/question-library")
def question_suggestions(
    search: str = Query("", max_length=10000),
    limit: int = Query(8, ge=1, le=25),
    db: Session = Depends(get_db),
):
    from app.services import question_library
    return question_library.search(db, search, limit)


@router.post("/question-library")
def remember_question(
    data: QuestionInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.services import question_library
    question, created = question_library.remember(db, data)
    if created:
        forms.audit(db, admin.id, "question.create", "question", question.id, title=question.title)
    db.commit()
    return {"id": question.id, "created": created, "question": question_library.question_definition(question)}


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
                        "revision": v.revision,
                        "reporting_start": v.reporting_start.isoformat() if v.reporting_start else None,
                        "reporting_end": v.reporting_end.isoformat() if v.reporting_end else None,
                        "fields": sum(len(s.questions) for s in v.sections),
                        "section_count": len(v.sections),
                        "sections": [{"id": s.id} for s in v.sections],
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


@router.post("/forms/{form_id}/sections", status_code=201)
def add_section(
    form_id: int,
    title: str = Form(...),
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Add a new section to a form draft."""
    from app.services.forms import get_form, get_version

    form = get_form(db, form_id, True)
    if form.archived:
        raise HTTPException(409, "သိမ်းဆည်းထားသောပုံစံသို့ ကဏ္ဍ ထည့်၍ မရပါ။")

    version = form.versions[-1]
    if version.status != "draft":
        raise HTTPException(409, "မူကြမ်းဗားရှင်းများကိုသာ တည်းဖြတ်နိုင်သည်။")

    # Check if a section with this title already exists in this version
    existing = (
        db.query(FormSection)
        .filter(FormSection.version_id == version.id, FormSection.title == title)
        .first()
    )
    if existing:
        raise HTTPException(422, f"'{title}' အမည်ရှိ ကဏ္ဍ တစ်ခု ရှိပြီးဖြစ်သည်။")

    # Get the next position
    max_position = (
        db.query(func.max(FormSection.position))
        .filter(FormSection.version_id == version.id)
        .scalar()
    ) or -1

    section = FormSection(
        version_id=version.id,
        title=title,
        position=max_position + 1,
        enabled=True,
        conditions=None,
    )
    version.sections.append(section)
    db.flush()
    return {"id": section.id, "title": section.title, "position": section.position}


@router.post("/forms/{form_id}/sections/{section_id}/questions", status_code=201)
def add_questions_to_section(
    form_id: int,
    section_id: int,
    question_ids: list[int] = Body(...),
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Add multiple questions from the question bank to a form section."""
    from app.services.forms import get_form, get_version

    form = get_form(db, form_id, True)
    if form.archived:
        raise HTTPException(409, "သိမ်းဆည်းထားသောပုံစံသို့ မေးခွန်းများ ထည့်၍ မရပါ။")

    version = get_version(db, form_id, None)

    # Find the section
    section = None
    for s in version.sections:
        if s.id == section_id:
            section = s
            break

    if not section:
        raise HTTPException(404, "ကဏ္ဍ မတွေ့ပါ။")

    # Get existing question keys in this section to prevent duplicates
    existing_keys = {q.key for s in version.sections for q in s.questions}

    added = []
    for q_id in question_ids:
        bank_question = db.get(QuestionBankQuestion, q_id)
        if not bank_question:
            raise HTTPException(404, f"မေးခွန်းဘဏ် မေးခွန်း {q_id} ကို မတွေ့ပါ။")

        # Check if a question with same key already exists
        key = bank_question.title[:50].strip().lower().replace(" ", "_")[:50] or f"q_{len(existing_keys)}"
        # Make key unique
        unique_key = key
        counter = 1
        while unique_key in existing_keys:
            unique_key = f"{key}_{counter}"
            counter += 1

        question = FormField(
            version_id=version.id,
            section_id=section.id,
            key=unique_key,
            title=bank_question.title,
            title_my=bank_question.title_my,
            title_en=bank_question.title_en,
            kind=bank_question.kind,
            help_text=bank_question.help_text,
            placeholder=bank_question.placeholder,
            required=bank_question.required,
            enabled=bank_question.enabled,
            config=bank_question.config,
            conditions=bank_question.conditions,
            source_university_question_id=bank_question.source_university_question_id,
            question_bank_id=bank_question.id,
        )
        db.add(question)
        existing_keys.add(unique_key)
        added.append(
            {
                "id": question.id,
                "key": question.key,
                "title": question.title,
                "kind": question.kind,
            }
        )

    db.commit()
    return {"added": added, "section_id": section.id}


@router.delete("/forms/{form_id}", status_code=204)
def delete_form(
    form_id: int,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    forms.delete_forms(db, [form_id], admin.id)


# Ministry/University management using persistent schema tables
ministry_table = persistent_metadata.tables["ministry"]
university_table = persistent_metadata.tables["university"]


class OrgInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(default="", max_length=100)  # for university: uniType


@router.get("/departments")
def list_departments(
    search: str = "",
    type: str = Query("", pattern="^(university|ministry)?$"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    directory = union_all(
        select(university_table.c.uniId.label('id'), university_table.c.uniName.label('name'),
               university_table.c.uniType.label('type'), literal('university').label('organization')),
        select(ministry_table.c.ministryId.label('id'), ministry_table.c.ministryName.label('name'),
               literal('').label('type'), literal('ministry').label('organization')),
    ).subquery()
    criteria = [directory.c.name.contains(search)] if search else []
    counts = dict(db.native.execute(select(directory.c.organization, func.count())
                  .where(*criteria).group_by(directory.c.organization)).all())
    if type:
        criteria.append(directory.c.organization == type)
    query = select(directory).where(*criteria)
    total = db.native.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    items = db.native.execute(query.order_by(directory.c.name, directory.c.organization, directory.c.id)
                              .offset((page - 1) * limit).limit(limit)).mappings().all()
    return {'total': total, 'counts': counts, 'items': [dict(row) for row in items]}


@router.get("/ministries")
def list_ministries(
    search: str = "",
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = select(ministry_table)
    if search:
        query = query.where(ministry_table.c.ministryName.contains(search))
    total = db.native.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    rows = db.native.execute(
        query.order_by(ministry_table.c.ministryName)
        .offset((page - 1) * limit).limit(limit)
    ).all()
    return {
        "total": total,
        "items": [
            {
                "id": r.ministryId,
                "name": r.ministryName,
                "type": "ministry",
            }
            for r in rows
        ],
    }


@router.post("/ministries", status_code=201)
def create_ministry(
    data: OrgInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    exists = db.native.execute(select(ministry_table).where(ministry_table.c.ministryName == data.name)).first()
    if exists:
        raise HTTPException(409, "Ministry with this name already exists.")
    result = db.native.execute(ministry_table.insert().values(ministryName=data.name))
    new_id = result.inserted_primary_key[0]
    forms.audit(db, admin.id, "ministry.create", "ministry", new_id, name=data.name)
    db.commit()
    return {"id": new_id, "name": data.name}


@router.put("/ministries/{ministry_id}")
def update_ministry(
    ministry_id: int,
    data: OrgInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ministry = db.native.execute(select(ministry_table).where(ministry_table.c.ministryId == ministry_id)).first()
    if not ministry:
        raise HTTPException(404, "Ministry not found.")
    if data.name != ministry.ministryName and db.native.execute(select(ministry_table).where(ministry_table.c.ministryName == data.name)).first():
        raise HTTPException(409, "Ministry with this name already exists.")
    db.native.execute(
        ministry_table.update()
        .where(ministry_table.c.ministryId == ministry_id)
        .values(ministryName=data.name)
    )
    forms.audit(db, admin.id, "ministry.update", "ministry", ministry_id, name=data.name)
    db.commit()
    return {"id": ministry_id, "name": data.name}


@router.delete("/ministries/{ministry_id}", status_code=204)
def delete_ministry(
    ministry_id: int,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ministry = db.native.execute(select(ministry_table).where(ministry_table.c.ministryId == ministry_id)).first()
    if not ministry:
        raise HTTPException(404, "Ministry not found.")
    # Check if ministry is used by any forms
    form_count = db.query(SurveyForm).filter(SurveyForm.audience == "ministry").count()
    if form_count > 0:
        raise HTTPException(
            409,
            f"Cannot delete ministry: {form_count} form(s) use ministry audience. Update or archive them first.",
        )
    forms.audit(db, admin.id, "ministry.delete", "ministry", ministry_id, name=ministry.ministryName)
    db.native.execute(ministry_table.delete().where(ministry_table.c.ministryId == ministry_id))
    db.commit()


@router.get("/universities")
def list_universities(
    search: str = "",
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = select(university_table)
    if search:
        query = query.where(university_table.c.uniName.contains(search))
    total = db.native.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    rows = db.native.execute(
        query.order_by(university_table.c.uniName)
        .offset((page - 1) * limit).limit(limit)
    ).all()
    return {
        "total": total,
        "items": [
            {
                "id": r.uniId,
                "name": r.uniName,
                "type": r.uniType,
            }
            for r in rows
        ],
    }


@router.post("/universities", status_code=201)
def create_university(
    data: OrgInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    exists = db.native.execute(select(university_table).where(university_table.c.uniName == data.name)).first()
    if exists:
        raise HTTPException(409, "University with this name already exists.")
    uni_type = data.type or "Unspecified"
    result = db.native.execute(university_table.insert().values(uniName=data.name, uniType=uni_type))
    new_id = result.inserted_primary_key[0]
    forms.audit(db, admin.id, "university.create", "university", new_id, name=data.name, type=uni_type)
    db.commit()
    return {"id": new_id, "name": data.name, "type": uni_type}


@router.put("/universities/{uni_id}")
def update_university(
    uni_id: int,
    data: OrgInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    uni = db.native.execute(select(university_table).where(university_table.c.uniId == uni_id)).first()
    if not uni:
        raise HTTPException(404, "University not found.")
    if data.name != uni.uniName and db.native.execute(select(university_table).where(university_table.c.uniName == data.name)).first():
        raise HTTPException(409, "University with this name already exists.")
    uni_type = data.type or uni.uniType
    db.native.execute(
        university_table.update()
        .where(university_table.c.uniId == uni_id)
        .values(uniName=data.name, uniType=uni_type)
    )
    forms.audit(db, admin.id, "university.update", "university", uni_id, name=data.name, type=uni_type)
    db.commit()
    return {"id": uni_id, "name": data.name, "type": uni_type}


@router.delete("/universities/{uni_id}", status_code=204)
def delete_university(
    uni_id: int,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    uni = db.native.execute(select(university_table).where(university_table.c.uniId == uni_id)).first()
    if not uni:
        raise HTTPException(404, "University not found.")
    # Check if university is used by any forms
    form_count = db.query(SurveyForm).filter(SurveyForm.audience == "university").count()
    if form_count > 0:
        raise HTTPException(
            409,
            f"Cannot delete university: {form_count} form(s) use university audience. Update or archive them first.",
        )
    forms.audit(db, admin.id, "university.delete", "university", uni_id, name=uni.uniName)
    db.native.execute(university_table.delete().where(university_table.c.uniId == uni_id))
    db.commit()


class BulkDeleteFormsInput(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)


@router.post("/forms/bulk-delete", status_code=204)
def bulk_delete_forms(
    data: BulkDeleteFormsInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    forms.delete_forms(db, data.ids, admin.id)


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


@router.get("/reports/university")
def university_report_summary(
    recent_limit: int = Query(8, ge=1, le=25),
    db: Session = Depends(get_db),
):
    return university_reports.university_activity(db, recent_limit)


@router.get("/reports/university/{year_id}/universities")
def university_report_roster(
    year_id: int,
    state: str = Query("answered", pattern="^(answered|pending)$"),
    db: Session = Depends(get_db),
):
    roster = university_reports.university_year_roster(db, year_id, state)
    if roster is None:
        raise HTTPException(404, "Active university survey year not found.")
    return roster


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
                        label(detail["status"]),
                        detail["username"],
                        detail["created_at"],
                        detail["reporting_start"],
                        detail["reporting_end"],
                        section["title"],
                        a["key"],
                        a["title"],
                        a["display_value"],
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
    uni_id: int | None = None
    ministry_id: int | None = None


class AdministratorInput(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    is_active: bool = True
    password: str | None = Field(default=None, min_length=8, max_length=1024)


class PasswordChangeInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=8, max_length=1024)


def administrator_role(db: Session) -> UserRole:
    from app.config import settings

    role = db.query(UserRole).filter(UserRole.name == settings.ADMIN_ROLE_NAME).first()
    if not role:
        raise HTTPException(409, "Administrator role is not configured.")
    return role


def administrator_payload(account: User) -> dict:
    return {
        "id": account.id,
        "username": account.username,
        "is_active": account.is_active,
        "created_at": account.created_at.isoformat(),
    }


@router.get("/administrators")
def list_administrators(
    search: str = Query("", max_length=100),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(User).filter(User.role_id == administrator_role(db).id)
    if search.strip():
        query = query.filter(User.username.contains(search.strip()))
    return {
        "total": query.count(),
        "items": [administrator_payload(account) for account in
                  query.order_by(User.id.desc()).offset((page - 1) * limit).limit(limit)],
    }


@router.get("/administrators/{administrator_id}")
def get_administrator(administrator_id: int, db: Session = Depends(get_db)):
    account = db.query(User).filter(
        User.id == administrator_id, User.role_id == administrator_role(db).id
    ).first()
    if not account:
        raise HTTPException(404, "Administrator not found.")
    return administrator_payload(account)


@router.post("/administrators", status_code=201)
def create_administrator(
    data: AdministratorInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    username = data.username.strip()
    if not username or not data.password:
        raise HTTPException(422, "Enter a username and a password of at least 8 characters.")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(409, "Username already exists.")
    account = User(
        username=username, role_id=administrator_role(db).id,
        is_active=data.is_active, password_hash=hash_password(data.password),
    )
    db.add(account)
    db.flush()
    forms.audit(db, admin.id, "administrator.create", "user", account.id,
                username=username, is_active=data.is_active)
    db.commit()
    return administrator_payload(account)


@router.put("/administrators/{administrator_id}")
def update_administrator(
    administrator_id: int,
    data: AdministratorInput,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    account = db.query(User).filter(
        User.id == administrator_id, User.role_id == administrator_role(db).id
    ).with_for_update().first()
    if not account:
        raise HTTPException(404, "Administrator not found.")
    username = data.username.strip()
    if not username:
        raise HTTPException(422, "Enter a username.")
    if administrator_id == admin.id and not data.is_active:
        raise HTTPException(409, "You cannot deactivate your own account.")
    if administrator_id == admin.id and data.password:
        raise HTTPException(409, "Use the current-password form to change your own password.")
    if db.query(User).filter(User.username == username, User.id != administrator_id).first():
        raise HTTPException(409, "Username already exists.")
    account.username = username
    account.is_active = data.is_active
    if data.password:
        account.password_hash = hash_password(data.password)
        from app.crud import admin_session
        admin_session.revoke_user_sessions(db, administrator_id)
    elif not data.is_active:
        from app.crud import admin_session
        admin_session.revoke_user_sessions(db, administrator_id)
    forms.audit(db, admin.id, "administrator.edit", "user", administrator_id,
                username=username, is_active=data.is_active, password_reset=bool(data.password))
    db.commit()
    return administrator_payload(account)


@router.delete("/administrators/{administrator_id}", status_code=204)
def delete_administrator(
    administrator_id: int,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.models.forms import AnswerFile

    account = db.query(User).filter(
        User.id == administrator_id, User.role_id == administrator_role(db).id
    ).with_for_update().first()
    if not account:
        raise HTTPException(404, "Administrator not found.")
    if administrator_id == admin.id:
        raise HTTPException(409, "You cannot delete your own account.")
    references = (
        db.query(Submission.id).filter(Submission.user_id == administrator_id).first()
        or db.query(WorkbookImport.id).filter(WorkbookImport.actor_id == administrator_id).first()
        or db.query(AnswerFile.id).filter(AnswerFile.user_id == administrator_id).first()
        or db.query(AuditLog.id).filter(AuditLog.actor_id == administrator_id).first()
    )
    if references:
        raise HTTPException(409, "This administrator has historical records. Deactivate the account instead.")
    from app.crud import admin_session, user
    admin_session.revoke_user_sessions(db, administrator_id)
    username = account.username
    user.delete_account(db, account)
    forms.audit(db, admin.id, "administrator.delete", "user", administrator_id,
                username=username)
    db.commit()


@router.post("/account/password")
def change_own_password(
    data: PasswordChangeInput,
    request: Request,
    admin: AdminIdentity = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.crud import admin_session
    from app.admin_auth import COOKIE_NAME

    account = db.query(User).filter(User.id == admin.id).with_for_update().first()
    if not account or not verify_password(data.current_password, account.password_hash):
        raise HTTPException(400, "Current password is incorrect.")
    if data.current_password == data.new_password:
        raise HTTPException(422, "Choose a different new password.")
    account.password_hash = hash_password(data.new_password)
    admin_session.revoke_user_sessions(
        db, admin.id, keep_token=request.cookies.get(COOKIE_NAME, "")
    )
    forms.audit(db, admin.id, "account.password.change", "user", admin.id)
    db.commit()
    return {"changed": True}


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
        "ministries": [dict(id=row.ministryId, name=row.ministryName) for row in db.native.execute(select(ministry_table))],
        "universities": [dict(id=row.uniId, name=row.uniName) for row in db.native.execute(select(university_table))],
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "role_id": u.role_id,
                "is_active": u.is_active,
                "uni_id": u.university_id,
                "ministry_id": u.ministry_id,
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
        university_id=data.uni_id,
        ministry_id=data.ministry_id,
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
    if account.id == admin.id and data.password:
        raise HTTPException(409, "Use Settings to change your own password.")
    if (
        db.query(User)
        .filter(User.username == data.username, User.id != user_id)
        .first()
    ):
        raise HTTPException(409, "Username already exists.")
    old_role_id = account.role_id
    account.username = data.username
    account.role_id = data.role_id
    account.is_active = data.is_active
    account.university_id = data.uni_id
    account.ministry_id = data.ministry_id
    if data.password:
        account.password_hash = hash_password(data.password)
    if data.password or not data.is_active or data.role_id != old_role_id:
        from app.crud import admin_session
        admin_session.revoke_user_sessions(db, user_id)
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
                "actor_name": (db.get(User, a.actor_id).username if a.actor_id and db.get(User, a.actor_id) else 'System' if a.actor_id is None else 'Deleted account'),
                "action_label": audit_action(a.action),
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

from app.models.native_forms import (Ministry, University, QuestionTitle, MinistryQuestion, UniQuestion, Year, MinistrySurvey, UniSurvey)

@router.get("/questions")
def list_questions(
    search: str = "",
    type: str = Query("", pattern="^(university|ministry)?$"),
    year_id: int | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List questions from both university and ministry tables."""
    db = Session(bind=db.native)
    items = []
    total = 0

    if type in ("", "university"):
        query = db.query(UniQuestion).join(QuestionTitle, UniQuestion.qTID == QuestionTitle.qTID)
        if search:
            query = query.filter(UniQuestion.uQDetail.contains(search) | QuestionTitle.qTDetail.contains(search))
        if year_id:
            query = query.filter(UniQuestion.yID == year_id)
        total += query.count()
        for q in query.order_by(UniQuestion.uQId.desc()).offset((page - 1) * limit).limit(limit):
            title = db.get(QuestionTitle, q.qTID) if q.qTID else None
            items.append({
                "id": q.uQId,
                "detail": q.uQDetail,
                "type": "university",
                "title_id": q.qTID,
                "title_detail": title.qTDetail if title else None,
                "year_id": q.yID,
            })

    if type in ("", "ministry"):
        query = db.query(MinistryQuestion).join(QuestionTitle, MinistryQuestion.qTID == QuestionTitle.qTID)
        if search:
            query = query.filter(MinistryQuestion.mQDetail.contains(search) | QuestionTitle.qTDetail.contains(search))
        if year_id:
            query = query.filter(MinistryQuestion.yID == year_id)
        total += query.count()
        for q in query.order_by(MinistryQuestion.mQId.desc()).offset((page - 1) * limit).limit(limit):
            title = db.get(QuestionTitle, q.qTID) if q.qTID else None
            items.append({
                "id": q.mQId,
                "detail": q.mQDetail,
                "type": "ministry",
                "title_id": q.qTID,
                "title_detail": title.qTDetail if title else None,
                "year_id": q.yID,
            })

    return {"total": total, "items": items}

@router.get("/questions/years")
def list_question_years(db: Session = Depends(get_db)):
    """Get years that have questions."""
    db = Session(bind=db.native)
    years = db.query(Year).filter(Year.status == 1).all()
    return [{"yID": y.yID, "yearFrom": y.yearFrom, "yearTo": y.yearTo} for y in years]

@router.get("/question-titles")
def list_question_titles(db: Session = Depends(get_db)):
    db = Session(bind=db.native)
    titles = db.query(QuestionTitle).all()
    return [{"qTID": t.qTID, "qTDetail": t.qTDetail, "description": t.description} for t in titles]

@router.get("/surveys")
def list_surveys(
    search: str = "",
    type: str = Query("", pattern="^(university|ministry)?$"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    db = Session(bind=db.native)
    items = []
    total = 0

    if type in ("", "university"):
        query = db.query(UniSurvey).join(University, UniSurvey.uniId == University.uniId).join(UniQuestion, UniSurvey.uQId == UniQuestion.uQId)
        if search:
            query = query.filter(University.uniName.contains(search) | UniQuestion.uQDetail.contains(search))
        total += query.count()
        for s in query.order_by(UniSurvey.submittedAt.desc()).offset((page - 1) * limit).limit(limit):
            uni = db.get(University, s.uniId)
            q = db.get(UniQuestion, s.uQId)
            items.append({
                "id": s.uniSurveyId,
                "type": "university",
                "organization": uni.uniName if uni else None,
                "question": q.uQDetail if q else None,
                "hasItem": s.hasItem,
                "itemCount": s.itemCount,
                "submittedAt": s.submittedAt,
                "updatedAt": s.updatedAt,
            })

    if type in ("", "ministry"):
        query = db.query(MinistrySurvey).join(Ministry, MinistrySurvey.ministryId == Ministry.ministryId).join(MinistryQuestion, MinistrySurvey.mQId == MinistryQuestion.mQId)
        if search:
            query = query.filter(Ministry.ministryName.contains(search) | MinistryQuestion.mQDetail.contains(search))
        total += query.count()
        for s in query.order_by(MinistrySurvey.submittedAt.desc()).offset((page - 1) * limit).limit(limit):
            min_ = db.get(Ministry, s.ministryId)
            q = db.get(MinistryQuestion, s.mQId)
            items.append({
                "id": s.mSurveyId,
                "type": "ministry",
                "organization": min_.ministryName if min_ else None,
                "question": q.mQDetail if q else None,
                "hasItem": s.hasItem,
                "itemCount": s.itemCount,
                "submittedAt": s.submittedAt,
                "updatedAt": s.updatedAt,
            })

    return {"total": total, "items": items}

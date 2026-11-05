"""Transactional form editing, immutable publication and explicit version snapshots."""

from copy import deepcopy
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import update, select, func
from sqlalchemy.orm import selectinload

from app.models.forms import (
    AuditLog,
    FieldAnswer,
    FieldOption,
    FormField,
    FormSection,
    FormVersion,
    Submission,
    SurveyForm,
    WorkbookImport,
    QuestionBankQuestion,
)
from app.schemas.forms import DraftInput, SectionInput, QuestionInput
from app.services.form_logic import SUPPORTED, validate_answers, validate_rules


def audit(db, actor, action, entity, target_id, **changes):
    db.add(
        AuditLog(
            actor_id=actor,
            action=action,
            entity=entity,
            target_id=target_id,
            changes=changes,
        )
    )


def get_form(db, form_id, lock=False):
    query = (
        db.query(SurveyForm)
        .options(
            selectinload(SurveyForm.versions)
            .selectinload(FormVersion.sections)
            .selectinload(FormSection.questions)
            .selectinload(FormField.options)
        )
        .filter(SurveyForm.id == form_id)
    )
    if lock:
        query = query.with_for_update()
    form = query.first()
    if not form:
        raise HTTPException(404, "Form not found.")
    return form


def get_version(db, form_id, version_id=None):
    form = get_form(db, form_id)
    if version_id is None:
        version = (
            max(form.versions, key=lambda item: item.number) if form.versions else None
        )
    else:
        version = next((v for v in form.versions if v.id == version_id), None)
    if not version:
        raise HTTPException(404, "Form version not found.")
    return version


def definition(version):
    return {
        "title": version.title,
        "description": version.description,
        "language": version.language,
        "starts_at": version.starts_at.isoformat() if version.starts_at else None,
        "ends_at": version.ends_at.isoformat() if version.ends_at else None,
        "revision": version.revision,
        "reporting_start": version.reporting_start.isoformat()
        if version.reporting_start
        else None,
        "reporting_end": version.reporting_end.isoformat()
        if version.reporting_end
        else None,
        "sections": [
            {
                "title": section.title,
                "description": section.description,
                "enabled": section.enabled,
                "conditions": section.conditions,
                "questions": [
                    {
                        "key": q.key,
                        "title": q.title,
                        "title_my": q.title_my,
                        "title_en": q.title_en,
                        "kind": q.kind,
                        "help_text": q.help_text,
                        "placeholder": q.placeholder,
                        "required": q.required,
                        "enabled": q.enabled,
                        "config": q.config,
                        "conditions": q.conditions,
                        "options": [
                            {"value": o.value, "label": o.label} for o in q.options
                        ],
                    }
                    for q in section.questions
                ],
            }
            for section in version.sections
        ],
    }


def version_payload(version):
    return {
        "id": version.id,
        "number": version.number,
        "status": version.status,
        "published_at": version.published_at.isoformat()
        if version.published_at
        else None,
        **definition(version),
    }


def form_payload(form):
    return {
        "id": form.id,
        "title": form.title,
        "audience": form.audience,
        "archived": form.archived,
        "versions": [version_payload(version) for version in form.versions],
    }


def apply_definition(db, version, data):
    try:
        validate_rules(data)
    except ValueError as error:
        raise HTTPException(422, str(error))
    sources = {
        q.key: q.source_university_question_id
        for section in version.sections
        for q in section.questions
    }
    version.title = data.title
    version.description = data.description
    version.language = data.language
    version.reporting_start = data.reporting_start
    version.reporting_end = data.reporting_end
    version.starts_at = data.starts_at.replace(tzinfo=None) if data.starts_at else None
    version.ends_at = data.ends_at.replace(tzinfo=None) if data.ends_at else None
    version.sections.clear()
    db.flush()
    for position, item in enumerate(data.sections):
        section = FormSection(
            version_id=version.id,
            position=position,
            **item.model_dump(exclude={"questions"}),
        )
        version.sections.append(section)
        for q_position, field in enumerate(item.questions):
            q = FormField(
                version_id=version.id,
                position=q_position,
                **field.model_dump(exclude={"options"}),
            )
            if q.key in sources:
                q.source_university_question_id = sources[q.key]
            section.questions.append(q)
            q.options = [
                FieldOption(position=i, **option.model_dump())
                for i, option in enumerate(field.options)
            ]


def create_form(db, data, actor):
    """Simple form creation - just title and template, system handles everything else."""
    import json
    from pathlib import Path

    # Check if using kid template
    if data.template == "kid_survey":
        content = json.loads(
            (Path(__file__).resolve().parents[1] / "data" / "kid_survey.json")
            .read_text(encoding="utf-8")
        )
        content["title"] = data.title
        initial = DraftInput.model_validate(content)
    elif data.template == "university_dedc":
        content = json.loads(
            (Path(__file__).resolve().parents[1] / "data" / "university_survey.json")
            .read_text(encoding="utf-8")
        )
        content["title"] = data.title
        initial = DraftInput.model_validate(content)
    else:
        # Blank form with minimal questions - kid friendly!
        initial = DraftInput(
            title=data.title,
            sections=[
                SectionInput(
                    title="Basic Information",
                    questions=[
                        QuestionInput(
                            key="name",
                            title="What is your name?",
                            kind="short_text",
                            required=True,
                        ),
                        QuestionInput(
                            key="age",
                            title="How old are you?",
                            kind="number",
                            required=True,
                            config={"min": 0, "max": 120},
                        ),
                    ],
                )
            ],
        )

    form = SurveyForm(title=data.title, audience=data.audience)
    form.versions.append(FormVersion(number=1, title=data.title))
    db.add(form)
    db.flush()
    if initial is not None:
        apply_definition(db, form.versions[0], initial)
    audit(db, actor, "form.create", "form", form.id, title=data.title)
    db.commit()
    return form


def save_draft(db, form_id, version_id, data, actor):
    form = get_form(db, form_id, True)
    version = get_version(db, form_id, version_id)
    if form.archived or version.status != "draft":
        raise HTTPException(
            409, "Only active drafts can be edited. Create a new version."
        )
    if version.revision != data.revision:
        raise HTTPException(
            409, "This draft changed in another window. Reload before saving."
        )
    changed = db.execute(
        update(FormVersion)
        .where(FormVersion.id == version.id, FormVersion.revision == data.revision)
        .values(revision=data.revision + 1),
        execution_options={"synchronize_session": False},
    )
    if changed.rowcount != 1:
        raise HTTPException(409, "Draft changed. Reload and try again.")
    before = {"title": version.title, "revision": data.revision}
    original = {
        q["key"]: q
        for section in definition(version)["sections"]
        for q in section["questions"]
    }
    updated = {
        q.key: q.model_dump() for section in data.sections for q in section.questions
    }
    apply_definition(db, version, data)
    version.revision = data.revision + 1
    form.title = data.title
    audit(
        db,
        actor,
        "form.edit",
        "version",
        version.id,
        before=before,
        after={"title": data.title, "revision": version.revision},
    )
    for key in original.keys() | updated.keys():
        if original.get(key) != updated.get(key):
            action = (
                "question.create"
                if key not in original
                else "question.delete"
                if key not in updated
                else "question.edit"
            )
            audit(
                db,
                actor,
                action,
                "version",
                version.id,
                question_key=key,
                before=original.get(key),
                after=updated.get(key),
            )
    db.commit()
    return version


def clone_version(db, form_id, actor):
    form = get_form(db, form_id, True)
    if form.archived:
        raise HTTPException(409, "Restore the form before creating a draft.")
    if any(v.status == "draft" for v in form.versions):
        raise HTTPException(409, "This form already has a draft.")
    source = get_version(db, form_id)
    version = FormVersion(form_id=form.id, number=source.number + 1, title=source.title)
    db.add(version)
    db.flush()
    apply_definition(db, version, DraftInput.model_validate(definition(source)))
    # Keep explicit legacy provenance across version copies.
    originals = {q.key: q for s in source.sections for q in s.questions}
    for section in version.sections:
        for q in section.questions:
            old = originals[q.key]
            q.source_university_question_id = old.source_university_question_id
    audit(db, actor, "form.version", "version", version.id, source_version=source.id)
    db.commit()
    return version


def publish(db, form_id, version_id, revision, actor):
    form = get_form(db, form_id, True)
    version = get_version(db, form_id, version_id)
    if form.archived or version.status != "draft":
        raise HTTPException(409, "Only an active draft can be published.")
    if revision != version.revision:
        raise HTTPException(409, "Draft changed. Review it again before publishing.")
    fields = [
        q
        for section in version.sections
        if section.enabled
        for q in section.questions
        if q.enabled
    ]
    if not fields:
        raise HTTPException(422, "Add at least one enabled question before publishing.")
    if any(q.kind not in SUPPORTED for q in fields):
        raise HTTPException(422, "Unsupported question type.")
    validate_rules(DraftInput.model_validate(definition(version)))
    version.status = "published"
    version.published_at = datetime.now(timezone.utc).replace(tzinfo=None)
    audit(db, actor, "form.publish", "version", version.id, number=version.number)
    db.commit()
    return version


def duplicate(db, form_id, actor):
    source = get_form(db, form_id)
    form = SurveyForm(title=(source.title + " (copy)")[:255], audience=source.audience)
    db.add(form)
    db.flush()
    version = FormVersion(form_id=form.id, number=1, title=form.title)
    db.add(version)
    db.flush()
    data = definition(get_version(db, source.id))
    data["title"] = form.title
    apply_definition(db, version, DraftInput.model_validate(data))
    audit(db, actor, "form.duplicate", "form", form.id, source_form=source.id)
    db.commit()
    return form


def delete_draft_form(db, form_id, actor):
    form = get_form(db, form_id, True)
    if any(v.status != "draft" for v in form.versions):
        raise HTTPException(
            409, "Published forms must be archived to preserve history."
        )
    ids = [v.id for v in form.versions]
    if db.query(WorkbookImport).filter(WorkbookImport.version_id.in_(ids)).first():
        raise HTTPException(
            409, "This form has preserved workbook observations. Archive it instead."
        )
    audit(db, actor, "form.delete", "form", form.id, title=form.title)
    db.delete(form)
    db.commit()


def delete_forms(db, form_ids, actor):
    """Validate the whole selection before deleting form-owned records atomically."""
    selected = [get_form(db, identifier, True) for identifier in dict.fromkeys(form_ids)]
    for form in selected:
        version_ids = [version.id for version in form.versions]
        if db.query(Submission).filter(Submission.version_id.in_(version_ids)).first():
            raise HTTPException(409, f"Cannot delete form '{form.title}': submissions exist. Archive the form instead.")
        if db.query(WorkbookImport).filter(WorkbookImport.version_id.in_(version_ids)).first():
            raise HTTPException(409, f"Cannot delete form '{form.title}': preserved workbook observations exist. Archive the form instead.")
    for form in selected:
        audit(db, actor, "form.delete", "form", form.id, title=form.title)
        # ORM cascades include field options; question bank entries remain independent.
        db.delete(form)
    db.commit()


def published_version(db, form_id):
    form = get_form(db, form_id)
    versions = [v for v in form.versions if v.status == "published"]
    if form.archived or not versions:
        raise HTTPException(404, "Published form not found.")
    version = max(versions, key=lambda v: v.number)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if (
        version.starts_at
        and now < version.starts_at
        or version.ends_at
        and now > version.ends_at
    ):
        raise HTTPException(409, "This form is outside its availability window.")
    return version


def submit(db, form_id, data, actor):
    version = published_version(db, form_id)
    clean = validate_answers(version, data.answers)
    from app.services.files import owned_files

    uploads = owned_files(db, version, clean, actor)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    started = (
        (
            data.started_at.astimezone(timezone.utc).replace(tzinfo=None)
            if data.started_at.tzinfo
            else data.started_at
        )
        if data.started_at
        else None
    )
    if started and started > now:
        raise HTTPException(422, "Start time cannot be in the future.")
    submission = Submission(
        version_id=version.id,
        user_id=actor,
        started_at=started,
        completed_at=now,
        location=data.location,
        reporting_start=data.reporting_start,
        reporting_end=data.reporting_end,
    )
    fields = {q.key: q.id for section in version.sections for q in section.questions}
    submission.answers = [
        FieldAnswer(field_id=fields[key], value=value) for key, value in clean.items()
    ]
    db.add(submission)
    db.flush()
    for attachment in uploads:
        attachment.submission_id = submission.id
    audit(
        db, actor, "submission.create", "submission", submission.id, version=version.id
    )
    db.commit()
    return submission


# ---- Question Bank Questions ----

def search_question_bank(db, query: str, page: int = 1, limit: int = 50):
    """Search the question bank by title with case-insensitive matching."""
    from sqlalchemy import func as sq_func
    from app.models.forms import QuestionBankQuestion, FormField, FormSection, FormVersion, SurveyForm

    page = max(1, page)
    limit = max(1, min(limit, 100))
    offset = (page - 1) * limit

    # Build search filter
    search_filter = (
        sq_func.lower(QuestionBankQuestion.title).contains(sq_func.lower(query))
        | QuestionBankQuestion.title.contains(query)
    )

    # Count question bank questions
    bank_count = (
        db.query(sq_func.count(QuestionBankQuestion.id))
        .filter(search_filter)
        .scalar() or 0
    )

    # Count form fields (questions from forms)
    form_field_count = (
        db.query(sq_func.count(FormField.id))
        .join(FormSection, FormField.section_id == FormSection.id)
        .join(FormVersion, FormSection.version_id == FormVersion.id)
        .join(SurveyForm, FormVersion.form_id == SurveyForm.id)
        .filter(
            sq_func.lower(FormField.title).contains(sq_func.lower(query))
            | FormField.title.contains(query)
        )
        .scalar() or 0
    )

    total = bank_count + form_field_count

    # Get question bank questions
    bank_items = (
        db.query(QuestionBankQuestion)
        .filter(search_filter)
        .order_by(QuestionBankQuestion.id.desc())
        .limit(limit)
        .offset(max(0, offset - bank_count) if offset < bank_count else 0)
        .all()
    )

    # Get form fields
    form_field_offset = max(0, offset - len(bank_items)) if offset < bank_count else offset - bank_count
    form_field_limit = max(0, limit - len(bank_items))

    form_field_items = []
    if form_field_limit > 0:
        form_field_items = (
            db.query(FormField, SurveyForm.title.label("form_title"), FormVersion.number.label("version_number"), SurveyForm.id.label("form_id"), FormVersion.status.label("version_status"))
            .join(FormSection, FormField.section_id == FormSection.id)
            .join(FormVersion, FormSection.version_id == FormVersion.id)
            .join(SurveyForm, FormVersion.form_id == SurveyForm.id)
            .filter(
                sq_func.lower(FormField.title).contains(sq_func.lower(query))
                | FormField.title.contains(query)
            )
            .order_by(FormField.id.desc())
            .limit(form_field_limit)
            .offset(form_field_offset)
            .all()
        )

    # Combine results - convert to dict format expected by UI
    items = []
    for q in bank_items:
        items.append({
            "id": q.id,
            "title": q.title,
            "title_my": q.title_my,
            "title_en": q.title_en,
            "kind": q.kind,
            "help_text": q.help_text,
            "placeholder": q.placeholder,
            "required": q.required,
            "enabled": q.enabled,
            "config": q.config,
            "question_bank_id": q.id,
            "form": None,
            "version": None,
            "form_id": None,
            "status": "bank",
        })

    for field, form_title, version_number, form_id, version_status in form_field_items:
        items.append({
            "id": field.id,
            "title": field.title,
            "title_my": field.title_my,
            "title_en": field.title_en,
            "kind": field.kind,
            "help_text": field.help_text,
            "placeholder": field.placeholder,
            "required": field.required,
            "enabled": field.enabled,
            "config": field.config,
            "question_bank_id": field.question_bank_id,
            "form": form_title,
            "version": version_number,
            "form_id": form_id,
            "status": version_status,
        })

    return {"total": total, "items": items, "page": page, "limit": limit, "pages": (total + limit - 1) // limit if total > 0 else 0}


def get_question_bank_question(db, question_id: int):
    """Get a single question bank question by ID."""
    return db.get(QuestionBankQuestion, question_id)


def create_question_bank_question(
    db,
    title: str,
    title_my: str = "",
    title_en: str = "",
    kind: str = "short_text",
    help_text: str = "",
    placeholder: str = "",
    required: bool = False,
    enabled: bool = True,
    config: dict | None = None,
) -> QuestionBankQuestion:
    """Create a new question in the question bank, preventing duplicates."""
    from sqlalchemy import select

    config = config or {}
    # Normalize title for duplicate check (trim whitespace, case-insensitive)
    normalized_title = title.strip()

    # Check for existing question with same title and kind (case-insensitive, whitespace-normalized)
    existing = (
        db.query(QuestionBankQuestion)
        .filter(
            func.lower(QuestionBankQuestion.title).func.collate("NOCASE") == normalized_title.lower(),
            QuestionBankQuestion.kind == kind,
        )
        .first()
    )

    if existing:
        # Update existing question's fields if they've changed
        existing.title_my = title_my or existing.title_my
        existing.title_en = title_en or existing.title_en
        existing.help_text = help_text or existing.help_text
        existing.placeholder = placeholder or existing.placeholder
        existing.required = required or existing.required
        existing.enabled = enabled and existing.enabled
        existing.config = {**existing.config, **config}
        existing.created_at = func.now()
        db.flush()
        return existing

    # Create new question bank question
    question = QuestionBankQuestion(
        title=normalized_title,
        title_my=title_my,
        title_en=title_en,
        kind=kind,
        help_text=help_text,
        placeholder=placeholder,
        required=required,
        enabled=enabled,
        config=config,
    )
    db.add(question)
    db.flush()
    return question


def update_question_bank_question(
    db,
    question_id: int,
    title: str | None = None,
    title_my: str | None = None,
    title_en: str | None = None,
    kind: str | None = None,
    help_text: str | None = None,
    placeholder: str | None = None,
    required: bool | None = None,
    enabled: bool | None = None,
    config: dict | None = None,
) -> QuestionBankQuestion:
    """Update a question bank question."""
    question = db.get(QuestionBankQuestion, question_id)
    if not question:
        raise HTTPException(404, "Question bank question not found.")

    if title is not None:
        question.title = title.strip()
    if title_my is not None:
        question.title_my = title_my
    if title_en is not None:
        question.title_en = title_en
    if kind is not None:
        question.kind = kind
    if help_text is not None:
        question.help_text = help_text
    if placeholder is not None:
        question.placeholder = placeholder
    if required is not None:
        question.required = required
    if enabled is not None:
        question.enabled = enabled
    if config is not None:
        question.config = {**question.config, **config}

    db.flush()
    return question


def delete_question_bank_question(db, question_id: int, check_usage: bool = True) -> bool:
    """Delete a question bank question. If check_usage, prevent deletion if used by forms."""
    question = db.get(QuestionBankQuestion, question_id)
    if not question:
        return False

    if check_usage:
        # Check if question is used by any form fields
        used_by = (
            db.query(FormField)
            .filter(FormField.question_bank_id == question_id)
            .count()
        )
        if used_by > 0:
            return False  # Prevent deletion - question is in use

    db.delete(question)
    db.flush()
    return True

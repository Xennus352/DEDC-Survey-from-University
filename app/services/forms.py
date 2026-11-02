"""Transactional form editing, immutable publication and explicit version snapshots."""

from copy import deepcopy
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import update
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
)
from app.schemas.forms import DraftInput
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
        q.key: (q.source_university_question_id, q.source_ministry_question_id)
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
                q.source_university_question_id, q.source_ministry_question_id = (
                    sources[q.key]
                )
            section.questions.append(q)
            q.options = [
                FieldOption(position=i, **option.model_dump())
                for i, option in enumerate(field.options)
            ]


def create_form(db, data, actor):
    form = SurveyForm(title=data.title, audience=data.audience)
    form.versions.append(FormVersion(number=1, title=data.title))
    db.add(form)
    db.flush()
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
            q.source_ministry_question_id = old.source_ministry_question_id
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

"""Bounded attachments with real ownership, version and field checks."""

from io import BytesIO
from pathlib import PurePath
from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError
from app.models.forms import AnswerFile
from app.services.forms import audit

MAX_FILE = 5 * 1024 * 1024


def upload(db, version, key, filename, content, actor):
    field = next(
        (
            q
            for section in version.sections
            for q in section.questions
            if q.key == key and q.enabled
        ),
        None,
    )
    if not field or field.kind not in {"file", "image"}:
        raise HTTPException(422, "Choose a file/image question in this version.")
    if not content or len(content) > MAX_FILE:
        raise HTTPException(413, "Files must be non-empty and at most 5 MB.")
    suffix = PurePath(filename or "").suffix.lower()
    allowed = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    if suffix not in allowed:
        raise HTTPException(
            422, "Supported files: PDF, TXT, CSV, DOCX, XLSX, PNG, JPEG and WebP."
        )
    if field.kind == "image" or allowed[suffix].startswith("image/"):
        try:
            with Image.open(BytesIO(content)) as image:
                if (
                    image.format not in {"PNG", "JPEG", "WEBP"}
                    or image.width * image.height > 40_000_000
                ):
                    raise ValueError()
                image.verify()
        except (
            UnidentifiedImageError,
            ValueError,
            OSError,
            Image.DecompressionBombError,
        ):
            raise HTTPException(422, "Upload a valid PNG, JPEG or WebP image.")
        if not allowed[suffix].startswith("image/"):
            raise HTTPException(422, "Image content and filename extension must match.")
    record = AnswerFile(
        version_id=version.id,
        field_id=field.id,
        field_key=field.key,
        user_id=actor,
        filename=PurePath(filename.replace("\\", "/")).name[:255],
        media_type=allowed[suffix],
        size=len(content),
        content=content,
    )
    db.add(record)
    db.flush()
    audit(
        db,
        actor,
        "file.upload",
        "file",
        record.id,
        version=version.id,
        bytes=len(content),
    )
    db.commit()
    return {"file_id": record.id, "filename": record.filename, "size": record.size}


def owned_files(db, version, answers, actor):
    rows = []
    for section in version.sections:
        for q in section.questions:
            if q.kind not in {"file", "image"} or q.key not in answers:
                continue
            value = answers[q.key]
            record = (
                db.query(AnswerFile)
                .filter_by(
                    id=value["file_id"],
                    user_id=actor,
                    version_id=version.id,
                    field_key=q.key,
                )
                .with_for_update()
                .first()
            )
            if not record or record.submission_id is not None:
                raise HTTPException(
                    422, "Attachment is unavailable or belongs to another response."
                )
            if q.kind == "image" and not record.media_type.startswith("image/"):
                raise HTTPException(422, "This question requires an image.")
            rows.append(record)
    return rows

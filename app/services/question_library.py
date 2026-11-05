"""Reusable question definitions across editor sessions and existing forms."""
from copy import deepcopy
import json

from app.models.forms import FormField, QuestionBankQuestion
from app.schemas.forms import QuestionInput


def normalized_title(title):
    return " ".join(title.split()).casefold()


def question_definition(question):
    return {
        "title": question.title,
        "title_my": question.title_my,
        "title_en": question.title_en,
        "kind": question.kind,
        "help_text": question.help_text,
        "placeholder": question.placeholder,
        "required": question.required,
        "enabled": question.enabled,
        "config": deepcopy(question.config),
        "options": deepcopy(question.options) if isinstance(question, QuestionBankQuestion) else [
            {"value": option.value, "label": option.label} for option in question.options
        ],
    }


def signature(definition):
    return json.dumps({**definition, "title": normalized_title(definition["title"])}, sort_keys=True, ensure_ascii=False)


def search(db, query, limit=8):
    needle = normalized_title(query)
    if not needle:
        return {"items": [], "total": 0}
    items, seen = [], set()
    # Python casefold handles Burmese text and Unicode consistently on SQLite/MySQL.
    for model, source in ((QuestionBankQuestion, "library"), (FormField, "form")):
        for question in db.query(model).order_by(model.id.desc()).all():
            if not any(needle in normalized_title(getattr(question, field)) for field in ("title", "title_my", "title_en")):
                continue
            data = question_definition(question)
            identity = signature(data)
            if identity in seen:
                continue
            seen.add(identity)
            if len(items) < limit:
                items.append({"id": question.id, "source": source, "question": data})
    return {"items": items, "total": len(seen)}


def remember(db, data: QuestionInput):
    """Reuse exact definitions; never overwrite settings on an existing question."""
    definition = data.model_dump(exclude={"key", "conditions"})
    definition["title"] = data.title.strip()
    if not definition["title"]:
        from fastapi import HTTPException
        raise HTTPException(422, "Enter a question title.")
    identity = signature(definition)
    for existing in db.query(QuestionBankQuestion).all():
        if signature(question_definition(existing)) == identity:
            return existing, False
    question = QuestionBankQuestion(**definition)
    db.add(question)
    db.flush()
    return question, True

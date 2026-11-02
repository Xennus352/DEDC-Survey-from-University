"""Workbook preview and draft-only import, retaining source answers verbatim."""

from datetime import date
from hashlib import sha256
from io import BytesIO
import re
from zipfile import ZipFile, BadZipFile

from fastapi import HTTPException
from app.models.forms import FormVersion, SurveyForm, WorkbookAnswer, WorkbookImport
from app.models.legacy import QuestionTitle, ReportingYear, UniversityQuestion
from app.schemas.forms import DraftInput
from app.services.forms import apply_definition, audit

MAX_UPLOAD = 10 * 1024 * 1024


def parse_workbook(content):
    from openpyxl import load_workbook

    if len(content) > MAX_UPLOAD:
        raise HTTPException(413, "Workbook exceeds 10 MB.")
    try:
        with ZipFile(BytesIO(content)) as archive:
            if (
                len(archive.infolist()) > 1000
                or sum(item.file_size for item in archive.infolist()) > 50_000_000
            ):
                raise HTTPException(413, "Expanded workbook is too large.")
        workbook = load_workbook(
            BytesIO(content), data_only=False, read_only=False, keep_links=False
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "Upload a valid .xlsx workbook.")
    sheets = []
    try:
        if len(workbook.worksheets) > 30:
            raise HTTPException(422, "At most 30 worksheets are supported.")
        for sheet in workbook.worksheets:
            if sheet.max_row > 5000 or sheet.max_column > 100:
                raise HTTPException(
                    422, "Worksheet dimensions exceed the import limit."
                )

            def value(row, col):
                cell = sheet.cell(row, col)
                if cell.data_type == "f":
                    raise HTTPException(
                        422,
                        f"{sheet.title}!{cell.coordinate}: formulas require review; replace with source values.",
                    )
                return str(cell.value) if cell.value is not None else ""

            headers = [value(4, c).strip() for c in range(1, 7)]
            if headers != ["စဉ်", "လုပ်ငန်းစဉ်", "ရှိ", "မရှိ", "အရေအတွက်", "အကြောင်းအရာ"]:
                sheets.append(
                    {
                        "worksheet": sheet.title,
                        "error": "Expected the six-column DEDC survey header on row 4.",
                    }
                )
                continue
            sections = []
            rows = []
            seen = set()
            warnings = [
                "English labels, required flags and dependency rules are not specified by this workbook.",
                "Quantity cells may contain compound text; imported as short text for review.",
                "Existing answers are preserved as source observations, not form defaults or new submissions.",
            ]
            for row in range(5, sheet.max_row + 1):
                number = value(row, 1).strip()
                title = value(row, 2)
                if number.isdigit() and title:
                    if number in seen:
                        raise HTTPException(
                            422, f"{sheet.title}: duplicate question number {number}."
                        )
                    seen.add(number)
                    if not sections:
                        raise HTTPException(
                            422, f"{sheet.title}: question before section heading."
                        )
                    answer = {
                        "number": number,
                        "question": title,
                        "source_cell": f"B{row}",
                        "present_text": value(row, 3),
                        "absent_text": value(row, 4),
                        "quantity_text": value(row, 5),
                        "details_text": value(row, 6),
                    }
                    rows.append(answer)
                    for suffix, label, kind in [
                        ("present", "ရှိ / မရှိ", "yes_no"),
                        ("quantity", "အရေအတွက်", "short_text"),
                        ("details", "အကြောင်းအရာ", "long_text"),
                    ]:
                        sections[-1]["questions"].append(
                            {
                                "key": f"q{number}_{suffix}",
                                "title": title + " — " + label,
                                "title_my": title + " — " + label,
                                "kind": kind,
                                "config": {
                                    "source_cell": f"B{row}",
                                    "source_number": number,
                                    "source_question": title,
                                    "source_component": suffix,
                                },
                            }
                        )
                elif number and not title:
                    sections.append({"title": number, "questions": []})
            if not rows:
                raise HTTPException(
                    422, f"{sheet.title}: no numbered question rows were detected."
                )
            title = (value(2, 1) + " — " + sheet.title)[-255:]
            from app.services.workbook_export import reporting_period

            period_start, period_end = reporting_period(sheet.title, value(3, 1))
            definition = DraftInput.model_validate(
                {
                    "title": title,
                    "description": value(1, 1) + "\n" + value(3, 1),
                    "sections": sections,
                    "reporting_start": period_start,
                    "reporting_end": period_end,
                }
            ).model_dump(mode="json")
            sheets.append(
                {
                    "worksheet": sheet.title,
                    "definition": definition,
                    "rows": rows,
                    "warnings": warnings,
                    "question_rows": len(rows),
                    "field_count": sum(len(s["questions"]) for s in sections),
                }
            )
    finally:
        workbook.close()
    return {"digest": sha256(content).hexdigest(), "sheets": sheets}


def import_sheet(db, preview, worksheet, definition, actor):
    sheet = next(
        (sheet for sheet in preview["sheets"] if sheet["worksheet"] == worksheet), None
    )
    if not sheet or "error" in sheet:
        raise HTTPException(422, "Select a supported worksheet.")
    if (
        db.query(WorkbookImport)
        .filter_by(digest=preview["digest"], worksheet=worksheet)
        .first()
    ):
        raise HTTPException(409, "This worksheet has already been imported.")
    form = SurveyForm(title=definition.title, audience="university")
    db.add(form)
    db.flush()
    version = FormVersion(form_id=form.id, number=1, title=definition.title)
    db.add(version)
    db.flush()
    apply_definition(db, version, definition)
    periods = re.findall(r"(20\d{2})", worksheet)
    if len(periods) == 2:
        start, end = date(int(periods[0]), 1, 1), date(int(periods[1]), 12, 31)
        period = db.query(ReportingYear).filter_by(start=start, end=end).first()
        if not period:
            period = ReportingYear(start=start, end=end)
            db.add(period)
            db.flush()
        for section in version.sections:
            category = db.query(QuestionTitle).filter_by(text=section.title).first()
            if not category:
                category = QuestionTitle(text=section.title)
                db.add(category)
                db.flush()
            section.source_title_id = category.id
            source_questions = {}
            for field in section.questions:
                original = field.config.get("source_question")
                if not original:
                    continue
                if original not in source_questions:
                    question = (
                        db.query(UniversityQuestion)
                        .filter_by(
                            text=original, year_id=period.id, title_id=category.id
                        )
                        .first()
                    )
                    if not question:
                        question = UniversityQuestion(
                            text=original, year_id=period.id, title_id=category.id
                        )
                        db.add(question)
                        db.flush()
                    source_questions[original] = question.id
                field.source_university_question_id = source_questions[original]
    imported = WorkbookImport(
        digest=preview["digest"],
        worksheet=worksheet,
        version_id=version.id,
        actor_id=actor,
    )
    imported.rows = [WorkbookAnswer(**row) for row in sheet["rows"]]
    db.add(imported)
    db.flush()
    audit(
        db,
        actor,
        "workbook.import",
        "form",
        form.id,
        worksheet=worksheet,
        question_rows=len(sheet["rows"]),
        source_digest=preview["digest"],
    )
    db.commit()
    return form

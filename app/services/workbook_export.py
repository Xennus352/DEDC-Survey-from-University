"""Export the original workbook layout, retaining its actual Excel formatting."""

from calendar import monthrange
from copy import copy
from datetime import date
from io import BytesIO
import re
from fastapi import HTTPException
from openpyxl import load_workbook
from app.models.forms import AnswerFile, FormVersion, Submission, WorkbookImport, WorkbookTemplate
from app.services.presentation import answer_text
from app.services.forms import get_version

MYANMAR_DIGITS = str.maketrans("0123456789", "၀၁၂၃၄၅၆၇၈၉")
MONTHS = [
    "ဇန်နဝါရီ",
    "ဖေဖော်ဝါရီ",
    "မတ်",
    "ဧပြီ",
    "မေ",
    "ဇွန်",
    "ဇူလိုင်",
    "ဩဂုတ်",
    "စက်တင်ဘာ",
    "အောက်တိုဘာ",
    "နိုဝင်ဘာ",
    "ဒီဇင်ဘာ",
]


def reporting_period(worksheet, heading):
    years = re.findall(r"20\d{2}", worksheet)
    if len(years) != 2:
        return None, None
    month = next((i + 1 for i, name in enumerate(MONTHS) if name + "လ" in heading), 12)
    return date(int(years[0]), 1, 1), date(
        int(years[1]), month, monthrange(int(years[1]), month)[1]
    )


def archive_template(db, content, filename):
    from hashlib import sha256

    digest = sha256(content).hexdigest()
    if not db.get(WorkbookTemplate, digest):
        db.add(
            WorkbookTemplate(digest=digest, filename=filename[:255], content=content)
        )
        db.flush()
    return digest


def original_workbook(db, include_answers):
    template = (
        db.query(WorkbookTemplate).order_by(WorkbookTemplate.created_at.desc()).first()
    )
    if not template:
        raise HTTPException(
            404, "Import an Excel workbook before exporting the original format."
        )
    if include_answers:
        return template.content
    book = load_workbook(BytesIO(template.content), keep_links=False)
    for sheet in book.worksheets:
        for row in range(5, sheet.max_row + 1):
            if (
                str(sheet.cell(row, 1).value or "").isdigit()
                and sheet.cell(row, 2).value
            ):
                for column in range(3, 7):
                    sheet.cell(row, column).value = None
    stream = BytesIO()
    book.save(stream)
    book.close()
    return stream.getvalue()


def grouped_questions(version):
    groups = []
    for section in version.sections:
        if not section.enabled:
            continue
        current = {}
        for question in section.questions:
            if not question.enabled:
                continue
            source = question.config.get("source_cell")
            key = source or f"field-{question.id}"
            if key not in current:
                group = {"section": section.title, "source_cell": source, "fields": []}
                current[key] = group
                groups.append(group)
            current[key]["fields"].append(question)
    return groups


def wording(group):
    labels = []
    for q in group["fields"]:
        title = (
            q.title.rsplit(" — ", 1)[0] if q.config.get("source_component") else q.title
        )
        if title not in labels:
            labels.append(title)
    return "\n".join(labels)


def period_heading(start, end):
    return f"({start.isoformat()} မှ {end.isoformat()} အထိ)".translate(MYANMAR_DIGITS)


def set_text(cell, value):
    cell.value = str(value) if value is not None else None
    if value is not None:
        cell.data_type = "s"


def answer_columns(group, values, db=None):
    columns = {3: None, 4: None, 5: None, 6: None}
    for q in group["fields"]:
        value = values.get(q.id)
        if value is None or value == "" or value == []:
            continue
        component = q.config.get("source_component")
        if component == "present" or q.kind == "yes_no":
            if value is True:
                columns[3] = "ရှိ"
            elif value is False:
                columns[4] = "မရှိ"
        elif component == "quantity" or q.kind in {"number", "decimal", "calculated"}:
            columns[5] = value
        else:
            attachment = db.get(AnswerFile, value['file_id']) if db is not None and q.kind in {'file', 'image'} and isinstance(value, dict) and value.get('file_id') else None
            columns[6] = answer_text(q, value, attachment.filename if attachment else None)
    return columns


def export_form(db, form_id, version_id=None, include_answers=False):
    version = get_version(db, form_id, version_id)
    source = (
        db.query(WorkbookImport)
        .join(FormVersion, FormVersion.id == WorkbookImport.version_id)
        .filter(FormVersion.form_id == form_id)
        .first()
    )
    template = (
        db.get(WorkbookTemplate, source.digest)
        if source
        else db.query(WorkbookTemplate)
        .order_by(WorkbookTemplate.created_at.desc())
        .first()
    )
    if not template:
        raise HTTPException(
            404, "Import the reference workbook to establish the exact Excel format."
        )
    book = load_workbook(BytesIO(template.content), keep_links=False)
    original = book[source.worksheet] if source else book.worksheets[0]
    for sheet in list(book.worksheets):
        if sheet != original:
            book.remove(sheet)
    groups = grouped_questions(version)
    source_cells = [
        f"B{row}"
        for row in range(5, original.max_row + 1)
        if str(original.cell(row, 1).value or "").isdigit()
        and original.cell(row, 2).value
    ]
    source_sections = [
        original.cell(row, 1).value
        for row in range(5, original.max_row + 1)
        if original.cell(row, 1).value
        and not str(original.cell(row, 1).value).isdigit()
        and not original.cell(row, 2).value
    ]
    section_titles = [
        section.title
        for section in version.sections
        if section.enabled and any(q.enabled for q in section.questions)
    ]
    same_layout = (
        bool(source)
        and [group["source_cell"] for group in groups] == source_cells
        and section_titles == source_sections
    )
    question_style = [copy(original.cell(6, column)._style) for column in range(1, 7)]
    section_style = copy(original["A5"]._style)
    question_height = original.row_dimensions[6].height
    section_height = original.row_dimensions[5].height
    source_period = reporting_period(original.title, str(original["A3"].value or ""))
    submissions = (
        db.query(Submission)
        .filter_by(version_id=version.id)
        .order_by(Submission.id)
        .limit(201)
        .all()
        if include_answers
        else []
    )
    if len(submissions) > 200:
        raise HTTPException(
            422, "Exact-format exports support up to 200 responses per workbook."
        )
    if include_answers and not submissions and not source:
        raise HTTPException(
            404, "There are no submitted answers for this form version."
        )
    targets = []
    if submissions:
        for submission in submissions:
            sheet = book.copy_worksheet(original)
            sheet.title = f"Response {submission.id}"
            targets.append((sheet, submission))
        book.remove(original)
    else:
        targets = [(original, None)]
    for sheet, submission in targets:
        # Preserve the original full institution heading for unchanged imports.
        original_title = (
            str(sheet["A2"].value or "")
            + " — "
            + (source.worksheet if source else sheet.title)
        )[-255:]
        if not source or version.title != original_title:
            set_text(sheet["A2"], version.title)
        start = submission.reporting_start if submission else version.reporting_start
        end = submission.reporting_end if submission else version.reporting_end
        if start and end and (start, end) != source_period:
            set_text(sheet["A3"], period_heading(start, end))
        values = (
            {answer.field_id: answer.value for answer in submission.answers}
            if submission
            else {}
        )
        if same_layout:
            for group in groups:
                row = sheet[group["source_cell"]].row
                set_text(sheet.cell(row, 2), wording(group))
                if not include_answers or submission:
                    columns = (
                        answer_columns(group, values, db)
                        if submission
                        else {column: None for column in range(3, 7)}
                    )
                    for column, value in columns.items():
                        if isinstance(value, (str, dict, list)):
                            set_text(sheet.cell(row, column), value)
                        else:
                            sheet.cell(row, column).value = value
        else:
            # Expand/reorder sections dynamically, borrowing the source row styles.
            for merged in list(sheet.merged_cells.ranges):
                if merged.min_row >= 5:
                    sheet.unmerge_cells(str(merged))
            for row in sheet.iter_rows(min_row=5):
                for cell in row:
                    cell.value = None
            number = 0
            row = 5
            last_section = None
            original_answers = (
                {item.number: item for item in source.rows} if source else {}
            )
            for group in groups:
                if group["section"] != last_section:
                    sheet.merge_cells(
                        start_row=row, start_column=1, end_row=row, end_column=6
                    )
                    cell = sheet.cell(row, 1)
                    cell._style = copy(section_style)
                    set_text(cell, group["section"])
                    sheet.row_dimensions[row].height = section_height
                    last_section = group["section"]
                    row += 1
                number += 1
                for column, style in enumerate(question_style, 1):
                    sheet.cell(row, column)._style = copy(style)
                sheet.row_dimensions[row].height = question_height
                sheet.cell(row, 1).value = number
                set_text(sheet.cell(row, 2), wording(group))
                columns = answer_columns(group, values, db) if submission else {}
                if include_answers and not submission:
                    source_number = group["fields"][0].config.get("source_number")
                    answer = original_answers.get(source_number)
                    if answer:
                        columns = {
                            3: answer.present_text,
                            4: answer.absent_text,
                            5: answer.quantity_text,
                            6: answer.details_text,
                        }
                for column in range(3, 7):
                    value = columns.get(column)
                    if isinstance(value, str):
                        set_text(sheet.cell(row, column), value)
                    else:
                        sheet.cell(row, column).value = value
                row += 1
            sheet.print_area = f"A1:F{max(row - 1, 4)}"
    stream = BytesIO()
    book.save(stream)
    book.close()
    return stream.getvalue()

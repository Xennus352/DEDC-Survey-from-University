"""Excel output matching the official native survey form layout.

The public survey prints on the six-column DEDC form (number,
process/question, present, absent, count and details).  The reference workbook
is kept as a small styled template so exported answers keep the same fonts,
borders, merged headings and print settings as the form.
"""

from collections import Counter
from copy import copy
from datetime import datetime
from io import BytesIO
from math import ceil
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from app.services.ministry_reports import ministry_answer_detail
from app.services.survey_formatting import MYANMAR_MONTHS, to_myanmar_number
from app.services.university_reports import university_answer_detail


TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "university_survey_report_template.xlsx"
)
SURVEY_TITLE_SUFFIX = (
    "တွင် ဆောင်ရွက်လျက်ရှိသည့် ဒီဂျစ်တယ်စီးပွားရေးဖွံ့ဖြိုးတိုးတက်မှုဆိုင်ရာ "
    "စစ်တမ်း"
)
SUBMITTED_LABEL = "တင်သွင်းသည့် ရက်စွဲ"


def _parse_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)
    return parsed


def _burmese_date(value):
    parsed = _parse_datetime(value)
    if parsed is None:
        return "မရှိပါ"
    month = MYANMAR_MONTHS.get(parsed.month, "")
    return " ".join(
        part
        for part in (
            to_myanmar_number(parsed.day),
            month,
            to_myanmar_number(parsed.year),
        )
        if part
    )


def _period_heading(detail):
    label = detail.get("period_heading") or detail.get("year_label") or ""
    return f"({label})" if label else ""


def _sheet_name(detail, entity_label):
    year_from = detail.get("year_from")
    year_to = detail.get("year_to")
    if year_from and year_to:
        name = f"{entity_label} ({year_from}-{year_to})"
    elif year_from:
        name = f"{entity_label} ({year_from})"
    else:
        name = f"{entity_label} answers"
    return name[:31]


def _title_block(detail, entity_key):
    organization = detail[entity_key][entity_key]
    submitted = _burmese_date(detail.get("last_submitted_at"))
    period = _period_heading(detail)
    submission = f"{SUBMITTED_LABEL} - {submitted}"
    return (
        f"{organization}{SURVEY_TITLE_SUFFIX}",
        " | ".join(part for part in (period, submission) if part),
    )


def _answer_values(question):
    number = question["number"]
    text = question["question"]
    answer = question.get("answer") or {}
    if not question.get("answered") or not answer:
        return [number, text, None, None, None, None]

    has_item = bool(answer.get("has_item"))
    item_count = answer.get("item_count")
    description = answer.get("description")
    remark = answer.get("remark")
    # Column 5 (အရေအတွက်) = item_count
    # Column 6 (အကြောင်းအရာ) = description (or remark if no description)
    details = str(description).strip() if description else (str(remark).strip() if remark else None)
    return [
        number,
        text,
        "ရှိ" if has_item else None,
        None if has_item else "မရှိ",
        item_count,
        details,
    ]


def _row_height(values, widths):
    lines = 1
    for value, width in zip(values, widths):
        if value is None:
            continue
        text = str(value)
        explicit = text.count("\n") + 1
        estimated = sum(
            max(1, ceil(len(line) / max(1, width * 0.8)))
            for line in text.split("\n")
        )
        lines = max(lines, explicit, estimated)
    return max(27, min(180, 18 * min(lines, 8) + 6))


def _dominant_styles(sheet, rows, fallback_row):
    if not rows:
        rows = [fallback_row]
    styles = []
    for column in range(1, 7):
        counts = Counter()
        values = {}
        for row in rows:
            style = copy(sheet.cell(row, column)._style)
            key = tuple(style)
            counts[key] += 1
            values.setdefault(key, style)
        styles.append(values[counts.most_common(1)[0][0]])
    return styles


def _template_metrics(sheet):
    widths = [
        sheet.column_dimensions[get_column_letter(column)].width or 10
        for column in range(1, 7)
    ]
    section_rows = []
    question_rows = []
    section_heights = {}
    section_heights_by_order = []
    section_styles_by_order = []
    question_heights = {}
    question_heights_by_number = {}
    question_styles_by_number = {}
    for row in range(5, sheet.max_row + 1):
        number = sheet.cell(row, 1).value
        question = sheet.cell(row, 2).value
        height = sheet.row_dimensions[row].height
        if str(number or "").isdigit() and question:
            question_rows.append(row)
            question_heights[str(question)] = height
            question_heights_by_number[int(number)] = height
            question_styles_by_number[int(number)] = [
                copy(sheet.cell(row, column)._style)
                for column in range(1, 7)
            ]
        elif number and not str(number).isdigit():
            section_rows.append(row)
            section_heights[str(number)] = height
            section_heights_by_order.append(height)
            section_styles_by_order.append(
                [
                    copy(sheet.cell(row, column)._style)
                    for column in range(1, 7)
                ]
            )
    return (
        widths,
        _dominant_styles(sheet, section_rows, 5),
        _dominant_styles(sheet, question_rows, 6),
        section_heights,
        section_heights_by_order,
        section_styles_by_order,
        question_heights,
        question_heights_by_number,
        question_styles_by_number,
    )


def _clear_template_rows(sheet):
    for merged in list(sheet.merged_cells.ranges):
        if merged.min_row >= 5:
            sheet.unmerge_cells(str(merged))
    if sheet.max_row >= 5:
        sheet.delete_rows(5, sheet.max_row - 4)


def _answer_workbook(
    detail, entity_key, entity_label, entity_description
):
    book = load_workbook(TEMPLATE_PATH)
    sheet = book.worksheets[0]
    (
        widths,
        section_styles,
        question_styles,
        section_heights,
        section_heights_by_order,
        section_styles_by_order,
        question_heights,
        question_heights_by_number,
        question_styles_by_number,
    ) = _template_metrics(sheet)
    _clear_template_rows(sheet)

    title, period_and_submission = _title_block(detail, entity_key)
    sheet["A2"] = title
    sheet["A3"] = period_and_submission
    sheet.title = _sheet_name(detail, entity_label)

    row_number = 5
    question_count = detail["question_count"]
    group_count = len(detail["groups"])
    for group_index, group in enumerate(detail["groups"]):
        sheet.merge_cells(
            start_row=row_number,
            start_column=1,
            end_row=row_number,
            end_column=6,
        )
        group_styles = (
            section_styles_by_order[group_index]
            if group_count == len(section_styles_by_order)
            else section_styles
        )
        for column, style in enumerate(group_styles, start=1):
            sheet.cell(row_number, column)._style = copy(style)
        sheet.cell(row_number, 1, group["title"])
        section_height = section_heights.get(group["title"])
        if section_height is None and group_count == len(section_heights_by_order):
            section_height = section_heights_by_order[group_index]
        sheet.row_dimensions[row_number].height = section_height or 45
        row_number += 1

        for question in group["questions"]:
            values = _answer_values(question)
            row_styles = (
                question_styles_by_number.get(question["number"], question_styles)
                if question_count == len(question_styles_by_number)
                else question_styles
            )
            for column, (value, style) in enumerate(
                zip(values, row_styles), start=1
            ):
                cell = sheet.cell(row_number, column, value)
                cell._style = copy(style)
                if column in (5, 6) and value is not None:
                    text = str(value)
                    if "\n" in text or len(text) > 18:
                        alignment = copy(cell.alignment)
                        alignment.wrap_text = True
                        cell.alignment = alignment
            height = question_heights.get(question["question"])
            if height is None and question_count == len(question_heights_by_number):
                height = question_heights_by_number.get(question["number"])
            sheet.row_dimensions[row_number].height = (
                height or _row_height(values, widths)
            )
            row_number += 1

    sheet.print_title_rows = "4:4"

    organization = detail[entity_key][entity_key]
    book.properties.title = f"{organization} - DEDC {entity_label} Survey"
    book.properties.subject = entity_description
    book.properties.creator = "DEDC"
    book.properties.lastModifiedBy = "DEDC"
    book.properties.description = (
        f"{entity_label} survey answers exported in the original DEDC "
        "form layout."
    )

    stream = BytesIO()
    book.save(stream)
    return stream.getvalue()


def university_answer_workbook(db, year_id, university_id):
    """Return a university workbook in the survey-form layout, or ``None``."""
    detail = university_answer_detail(db, year_id, university_id)
    if detail is None:
        return None
    return _answer_workbook(
        detail,
        "university",
        "University",
        "University digital development survey",
    )


def ministry_answer_workbook(db, year_id, ministry_id):
    """Return a ministry workbook in the survey-form layout, or ``None``."""
    detail = ministry_answer_detail(db, year_id, ministry_id)
    if detail is None:
        return None
    return _answer_workbook(
        detail,
        "ministry",
        "Ministry",
        "Ministry digital development survey",
    )

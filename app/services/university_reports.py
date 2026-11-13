"""Read-only summaries for active university survey years.

The university survey stores one answer row per institution and question in
``unisurvey``. The reports page needs a year-level view of that data without
changing the native tables or the existing submission APIs.
"""

from sqlalchemy import and_, case, func, select

from app.services.survey_formatting import MYANMAR_MONTHS, to_myanmar_number
from app.storage import university_survey_schema as schema


def _burmese_year_month(value):
    year = getattr(value, "year", None)
    month = getattr(value, "month", 0)
    if not year:
        return ""
    year_text = to_myanmar_number(year)
    month_text = MYANMAR_MONTHS.get(month)
    if month_text:
        return f"{year_text} {month_text}လ"
    return year_text


def year_label(year_from, year_to):
    """Return the full Burmese survey period shown on the reports page."""
    start = _burmese_year_month(year_from)
    end = _burmese_year_month(year_to)
    if start and end:
        return f"{start}မှ {end}အထိ"
    return start or end or "ကာလ မသတ်မှတ်ထားပါ"


def period_heading(year_from, year_to):
    """Return the period wording used by the original survey workbook."""
    start = to_myanmar_number(year_from.year) if year_from else ""
    end = to_myanmar_number(year_to.year) if year_to else ""
    end_month = MYANMAR_MONTHS.get(year_to.month, "") if year_to else ""
    if start and end and year_from.year == year_to.year:
        if end_month:
            return f"{start} ခုနှစ်၊ {end_month}လအထိ"
        return f"{start} ခုနှစ်အထိ"
    if start and end:
        if end_month:
            return f"{start} ခုနှစ် မှ {end} ခုနှစ်၊ {end_month}လအထိ"
        return f"{start} ခုနှစ် မှ {end} ခုနှစ်အထိ"
    return start or end or ""


def _iso(value):
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _percent(value, total):
    if not total:
        return 0.0
    return round(min(100.0, max(0.0, value * 100 / total)), 1)


def _year_status(submitted, total, completion):
    if total and submitted >= total and completion >= 100:
        return "completed"
    if submitted:
        return "in_progress"
    return "not_started"


def university_year_roster(db, year_id, state):
    """Return the universities that have or have not submitted for a year."""
    if state not in {"answered", "pending"}:
        raise ValueError("Unsupported university roster state.")

    connection = db.native
    year_row = (
        connection.execute(
            select(
                schema.year.c.yID,
                schema.year.c.yearFrom,
                schema.year.c.yearTo,
            ).where(
                schema.year.c.yID == year_id,
                schema.year.c.status == 1,
            )
        )
        .mappings()
        .first()
    )
    if not year_row:
        return None

    question_count = (
        connection.execute(
            select(func.count(schema.uniquestion.c.uQId)).where(
                schema.uniquestion.c.yID == year_id
            )
        ).scalar()
        or 0
    )
    if not question_count:
        return None

    if state == "answered":
        roster = (
            connection.execute(
                select(
                    schema.university.c.uniId,
                    schema.university.c.uniName,
                    schema.university.c.uniType,
                    func.count(
                        func.distinct(schema.unisurvey.c.uQId)
                    ).label("answered_questions"),
                    func.max(schema.unisurvey.c.submittedAt).label(
                        "last_submitted_at"
                    ),
                )
                .select_from(
                    schema.unisurvey.join(
                        schema.university,
                        schema.university.c.uniId == schema.unisurvey.c.uniId,
                    ).join(
                        schema.uniquestion,
                        schema.uniquestion.c.uQId == schema.unisurvey.c.uQId,
                    )
                )
                .where(schema.uniquestion.c.yID == year_id)
                .group_by(
                    schema.university.c.uniId,
                    schema.university.c.uniName,
                    schema.university.c.uniType,
                )
                .order_by(
                    func.lower(schema.university.c.uniName),
                    schema.university.c.uniId,
                )
            )
            .mappings()
            .all()
        )
    else:
        has_answer = (
            select(schema.unisurvey.c.uniSurveyId)
            .select_from(
                schema.unisurvey.join(
                    schema.uniquestion,
                    schema.uniquestion.c.uQId == schema.unisurvey.c.uQId,
                )
            )
            .where(
                schema.unisurvey.c.uniId == schema.university.c.uniId,
                schema.uniquestion.c.yID == year_id,
            )
        )
        roster = (
            connection.execute(
                select(
                    schema.university.c.uniId,
                    schema.university.c.uniName,
                    schema.university.c.uniType,
                )
                .where(~has_answer.exists())
                .order_by(
                    func.lower(schema.university.c.uniName),
                    schema.university.c.uniId,
                )
            )
            .mappings()
            .all()
        )

    universities = []
    for row in roster:
        answered = int(row.get("answered_questions") or 0)
        completion = _percent(answered, question_count)
        universities.append(
            {
                "university_id": row["uniId"],
                "university": row["uniName"],
                "university_type": row["uniType"],
                "question_count": question_count,
                "answered_questions": answered,
                "completion_percent": completion,
                "last_submitted_at": _iso(row.get("last_submitted_at")),
                "status": _year_status(
                    answered, question_count, completion
                ),
            }
        )

    return {
        "year_id": year_row["yID"],
        "year_label": year_label(
            year_row["yearFrom"], year_row["yearTo"]
        ),
        "year_from": getattr(year_row["yearFrom"], "year", None),
        "year_to": getattr(year_row["yearTo"], "year", None),
        "question_count": question_count,
        "state": state,
        "total": len(universities),
        "universities": universities,
    }


def university_answer_detail(db, year_id, university_id):
    """Return every university question for a year with one university's answer."""
    connection = db.native
    year_row = (
        connection.execute(
            select(
                schema.year.c.yID,
                schema.year.c.yearFrom,
                schema.year.c.yearTo,
            ).where(
                schema.year.c.yID == year_id,
                schema.year.c.status == 1,
            )
        )
        .mappings()
        .first()
    )
    if not year_row:
        return None

    university_row = (
        connection.execute(
            select(
                schema.university.c.uniId,
                schema.university.c.uniName,
                schema.university.c.uniType,
            ).where(schema.university.c.uniId == university_id)
        )
        .mappings()
        .first()
    )
    if not university_row:
        return None

    rows = (
        connection.execute(
            select(
                schema.uniquestion.c.uQId,
                schema.uniquestion.c.uQDetail,
                schema.uniquestion.c.qTID,
                schema.questiontitle.c.qTDetail,
                schema.questiontitle.c.description.label("title_description"),
                schema.unisurvey.c.uniSurveyId,
                schema.unisurvey.c.hasItem,
                schema.unisurvey.c.itemCount,
                schema.unisurvey.c.surveyDescription,
                schema.unisurvey.c.remark,
                schema.unisurvey.c.submittedAt,
                schema.unisurvey.c.updatedAt,
            )
            .select_from(
                schema.uniquestion
                .outerjoin(
                    schema.questiontitle,
                    schema.questiontitle.c.qTID == schema.uniquestion.c.qTID,
                )
                .outerjoin(
                    schema.unisurvey,
                    and_(
                        schema.unisurvey.c.uQId == schema.uniquestion.c.uQId,
                        schema.unisurvey.c.uniId == university_id,
                    ),
                )
            )
            .where(schema.uniquestion.c.yID == year_id)
            .order_by(
                schema.uniquestion.c.qTID,
                schema.uniquestion.c.uQId,
            )
        )
        .mappings()
        .all()
    )
    if not rows:
        return None

    groups = []
    groups_by_key = {}
    answered_questions = 0
    has_item_questions = 0
    no_item_questions = 0
    last_submitted_at = None
    for number, row in enumerate(rows, start=1):
        answered = row["uniSurveyId"] is not None
        submitted_at = row["submittedAt"] if answered else None
        if answered:
            answered_questions += 1
            if row["hasItem"]:
                has_item_questions += 1
            else:
                no_item_questions += 1
            if submitted_at and (
                last_submitted_at is None or submitted_at > last_submitted_at
            ):
                last_submitted_at = submitted_at

        group_key = row["qTID"] if row["qTID"] is not None else "other"
        group = groups_by_key.get(group_key)
        if group is None:
            group = {
                "title_id": row["qTID"],
                "title": row["qTDetail"] or "အခြား မေးခွန်းများ",
                "description": row["title_description"] or "",
                "question_count": 0,
                "answered_questions": 0,
                "questions": [],
            }
            groups_by_key[group_key] = group
            groups.append(group)

        group["question_count"] += 1
        if answered:
            group["answered_questions"] += 1
        group["questions"].append(
            {
                "question_id": row["uQId"],
                "number": number,
                "question": row["uQDetail"],
                "answered": answered,
                "answer": (
                    {
                        "has_item": bool(row["hasItem"]),
                        "item_count": row["itemCount"],
                        "description": row["surveyDescription"],
                        "remark": row["remark"],
                        "submitted_at": _iso(row["submittedAt"]),
                        "updated_at": _iso(row["updatedAt"]),
                    }
                    if answered
                    else None
                ),
            }
        )

    question_count = len(rows)
    unanswered_questions = max(0, question_count - answered_questions)
    completion = _percent(answered_questions, question_count)
    return {
        "year_id": year_row["yID"],
        "year_label": year_label(
            year_row["yearFrom"], year_row["yearTo"]
        ),
        "period_heading": period_heading(
            year_row["yearFrom"], year_row["yearTo"]
        ),
        "year_from": getattr(year_row["yearFrom"], "year", None),
        "year_to": getattr(year_row["yearTo"], "year", None),
        "question_count": question_count,
        "answered_questions": answered_questions,
        "has_item_questions": has_item_questions,
        "no_item_questions": no_item_questions,
        "unanswered_questions": unanswered_questions,
        "has_item_percent": _percent(has_item_questions, question_count),
        "no_item_percent": _percent(no_item_questions, question_count),
        "unanswered_percent": _percent(unanswered_questions, question_count),
        "completion_percent": completion,
        "last_submitted_at": _iso(last_submitted_at),
        "status": _year_status(
            answered_questions, question_count, completion
        ),
        "university": {
            "university_id": university_row["uniId"],
            "university": university_row["uniName"],
            "university_type": university_row["uniType"],
        },
        "groups": groups,
    }


def question_answer_rates(db, year_id):
    """Build per-question has/has-not rates for one active survey year."""
    connection = db.native
    year_row = (
        connection.execute(
            select(
                schema.year.c.yID,
                schema.year.c.yearFrom,
                schema.year.c.yearTo,
            ).where(
                schema.year.c.yID == year_id,
                schema.year.c.status == 1,
            )
        )
        .mappings()
        .first()
    )
    if not year_row:
        return None

    total_universities = (
        connection.execute(
            select(func.count()).select_from(schema.university)
        ).scalar()
        or 0
    )
    answered_universities = (
        connection.execute(
            select(
                func.count(func.distinct(schema.unisurvey.c.uniId))
            )
            .select_from(
                schema.unisurvey.join(
                    schema.uniquestion,
                    schema.uniquestion.c.uQId == schema.unisurvey.c.uQId,
                )
            )
            .where(schema.uniquestion.c.yID == year_id)
        ).scalar()
        or 0
    )

    total_by_type = {
        row["uniType"]: int(row["total_universities"] or 0)
        for row in connection.execute(
            select(
                schema.university.c.uniType,
                func.count(schema.university.c.uniId).label(
                    "total_universities"
                ),
            ).group_by(schema.university.c.uniType)
        )
        .mappings()
        .all()
    }
    answered_by_type = {
        row["uniType"]: int(row["answered_universities"] or 0)
        for row in connection.execute(
            select(
                schema.university.c.uniType,
                func.count(
                    func.distinct(schema.unisurvey.c.uniId)
                ).label("answered_universities"),
            )
            .select_from(
                schema.university.join(
                    schema.unisurvey,
                    schema.unisurvey.c.uniId == schema.university.c.uniId,
                ).join(
                    schema.uniquestion,
                    schema.uniquestion.c.uQId == schema.unisurvey.c.uQId,
                )
            )
            .where(schema.uniquestion.c.yID == year_id)
            .group_by(schema.university.c.uniType)
        )
        .mappings()
        .all()
    }
    university_types = []
    for university_type, type_total in total_by_type.items():
        type_answered = min(
            type_total, answered_by_type.get(university_type, 0)
        )
        university_types.append(
            {
                "university_type": university_type,
                "total_universities": type_total,
                "answered_universities": type_answered,
                "not_answered_universities": max(
                    0, type_total - type_answered
                ),
                "answered_percent": _percent(type_answered, type_total),
                "not_answered_percent": _percent(
                    type_total - type_answered, type_total
                ),
            }
        )
    university_types.sort(
        key=lambda item: (
            -item["answered_universities"],
            -item["total_universities"],
            item["university_type"],
        )
    )

    answered_count = func.count(
        func.distinct(schema.unisurvey.c.uniId)
    ).label("answered_universities")
    has_item_count = func.count(
        func.distinct(
            case(
                (schema.unisurvey.c.hasItem.is_(True), schema.unisurvey.c.uniId)
            )
        )
    ).label("has_item_count")
    no_item_count = func.count(
        func.distinct(
            case(
                (schema.unisurvey.c.hasItem.is_(False), schema.unisurvey.c.uniId)
            )
        )
    ).label("no_item_count")

    rows = (
        connection.execute(
            select(
                schema.uniquestion.c.uQId,
                schema.uniquestion.c.uQDetail,
                schema.uniquestion.c.qTID,
                schema.questiontitle.c.qTDetail,
                schema.questiontitle.c.description.label("title_description"),
                answered_count,
                has_item_count,
                no_item_count,
            )
            .select_from(
                schema.uniquestion
                .outerjoin(
                    schema.questiontitle,
                    schema.questiontitle.c.qTID == schema.uniquestion.c.qTID,
                )
                .outerjoin(
                    schema.unisurvey,
                    schema.unisurvey.c.uQId == schema.uniquestion.c.uQId,
                )
            )
            .where(schema.uniquestion.c.yID == year_id)
            .group_by(
                schema.uniquestion.c.uQId,
                schema.uniquestion.c.uQDetail,
                schema.uniquestion.c.qTID,
                schema.questiontitle.c.qTDetail,
                schema.questiontitle.c.description,
            )
            .order_by(
                schema.uniquestion.c.qTID,
                schema.uniquestion.c.uQId,
            )
        )
        .mappings()
        .all()
    )
    if not rows:
        return None

    groups = []
    groups_by_key = {}
    for number, row in enumerate(rows, start=1):
        question_answered = int(row["answered_universities"] or 0)
        has_items = int(row["has_item_count"] or 0)
        no_items = int(row["no_item_count"] or 0)
        group_key = row["qTID"] if row["qTID"] is not None else "other"
        group = groups_by_key.get(group_key)
        if group is None:
            group = {
                "title_id": row["qTID"],
                "title": row["qTDetail"] or "အခြား မေးခွန်းများ",
                "description": row["title_description"] or "",
                "question_count": 0,
                "questions": [],
            }
            groups_by_key[group_key] = group
            groups.append(group)
        group["question_count"] += 1
        group["questions"].append(
            {
                "question_id": row["uQId"],
                "number": number,
                "question": row["uQDetail"],
                "answered_universities": question_answered,
                "unanswered_universities": max(
                    0, total_universities - question_answered
                ),
                "has_item_count": has_items,
                "no_item_count": no_items,
                "has_item_percent": _percent(has_items, question_answered),
                "no_item_percent": _percent(no_items, question_answered),
                "answered_percent": _percent(
                    question_answered, total_universities
                ),
            }
        )

    not_answered = max(0, total_universities - answered_universities)
    return {
        "year_id": year_row["yID"],
        "year_label": year_label(
            year_row["yearFrom"], year_row["yearTo"]
        ),
        "year_from": getattr(year_row["yearFrom"], "year", None),
        "year_to": getattr(year_row["yearTo"], "year", None),
        "question_count": len(rows),
        "total_universities": total_universities,
        "answered_universities": answered_universities,
        "not_answered_universities": not_answered,
        "answered_percent": _percent(
            answered_universities, total_universities
        ),
        "not_answered_percent": _percent(
            not_answered, total_universities
        ),
        "university_types": university_types,
        "groups": groups,
    }


def university_activity(db, recent_limit=8):
    """Build the university activity contract consumed by the reports page."""
    connection = db.native

    total_universities = (
        connection.execute(
            select(func.count()).select_from(schema.university)
        ).scalar()
        or 0
    )

    year_rows = (
        connection.execute(
            select(
                schema.year.c.yID,
                schema.year.c.yearFrom,
                schema.year.c.yearTo,
                func.count(schema.uniquestion.c.uQId).label("question_count"),
            )
            .join(
                schema.uniquestion,
                schema.uniquestion.c.yID == schema.year.c.yID,
            )
            .where(schema.year.c.status == 1)
            .group_by(
                schema.year.c.yID,
                schema.year.c.yearFrom,
                schema.year.c.yearTo,
            )
            .order_by(
                func.coalesce(schema.year.c.yearTo, schema.year.c.yearFrom).desc(),
                schema.year.c.yID.desc(),
            )
        )
        .mappings()
        .all()
    )

    year_ids = [row["yID"] for row in year_rows]
    stats_by_year = {}
    if year_ids:
        stats = (
            connection.execute(
                select(
                    schema.uniquestion.c.yID,
                    func.count(
                        func.distinct(schema.unisurvey.c.uniId)
                    ).label("submitted_universities"),
                    func.count(
                        func.distinct(schema.unisurvey.c.uQId)
                    ).label("answered_questions"),
                    func.count(schema.unisurvey.c.uniSurveyId).label("answer_rows"),
                    func.max(schema.unisurvey.c.submittedAt).label(
                        "last_submitted_at"
                    ),
                    func.sum(
                        func.coalesce(schema.unisurvey.c.itemCount, 0)
                    ).label("item_total"),
                )
                .select_from(
                    schema.uniquestion.outerjoin(
                        schema.unisurvey,
                        schema.unisurvey.c.uQId == schema.uniquestion.c.uQId,
                    )
                )
                .where(schema.uniquestion.c.yID.in_(year_ids))
                .group_by(schema.uniquestion.c.yID)
            )
            .mappings()
            .all()
        )
        stats_by_year = {row["yID"]: row for row in stats}

    question_counts = {
        row["yID"]: int(row["question_count"] or 0) for row in year_rows
    }
    active_years = []
    report_total = 0
    answer_total = 0
    question_total = 0
    last_activity = None
    expected_answers = 0

    for row in year_rows:
        year_id = row["yID"]
        questions = question_counts[year_id]
        stats = stats_by_year.get(year_id, {})
        submitted = int(stats.get("submitted_universities") or 0)
        answer_rows = int(stats.get("answer_rows") or 0)
        completion = _percent(submitted, total_universities)
        coverage = _percent(
            answer_rows, total_universities * questions
        )
        pending = max(0, total_universities - submitted)
        last_submitted = stats.get("last_submitted_at")
        active_years.append(
            {
                "year_id": year_id,
                "label": year_label(row["yearFrom"], row["yearTo"]),
                "year_from": getattr(row["yearFrom"], "year", None),
                "year_to": getattr(row["yearTo"], "year", None),
                "question_count": questions,
                "submitted_universities": submitted,
                "pending_universities": pending,
                "completion_percent": completion,
                "answer_coverage_percent": coverage,
                "answer_rows": answer_rows,
                "item_total": int(stats.get("item_total") or 0),
                "last_submitted_at": _iso(last_submitted),
                "status": _year_status(
                    submitted, total_universities, completion
                ),
            }
        )
        report_total += submitted
        answer_total += answer_rows
        question_total += questions
        expected_answers += total_universities * questions
        if last_submitted and (
            last_activity is None or last_submitted > last_activity
        ):
            last_activity = last_submitted

    participating = 0
    if year_ids:
        participating = (
            connection.execute(
                select(
                    func.count(func.distinct(schema.unisurvey.c.uniId))
                )
                .select_from(
                    schema.unisurvey.join(
                        schema.uniquestion,
                        schema.uniquestion.c.uQId == schema.unisurvey.c.uQId,
                    )
                )
                .where(schema.uniquestion.c.yID.in_(year_ids))
            ).scalar()
            or 0
        )

    recent_rows = []
    if year_ids:
        recent_rows = (
            connection.execute(
                select(
                    schema.university.c.uniId,
                    schema.university.c.uniName,
                    schema.university.c.uniType,
                    schema.uniquestion.c.yID,
                    func.count(
                        func.distinct(schema.unisurvey.c.uQId)
                    ).label("answered_questions"),
                    func.count(schema.unisurvey.c.uniSurveyId).label(
                        "answer_rows"
                    ),
                    func.max(schema.unisurvey.c.submittedAt).label(
                        "submitted_at"
                    ),
                    func.sum(
                        func.coalesce(schema.unisurvey.c.itemCount, 0)
                    ).label("item_total"),
                )
                .select_from(
                    schema.unisurvey.join(
                        schema.university,
                        schema.university.c.uniId == schema.unisurvey.c.uniId,
                    )
                    .join(
                        schema.uniquestion,
                        schema.uniquestion.c.uQId == schema.unisurvey.c.uQId,
                    )
                    .join(
                        schema.year,
                        schema.year.c.yID == schema.uniquestion.c.yID,
                    )
                )
                .where(schema.year.c.status == 1)
                .group_by(
                    schema.university.c.uniId,
                    schema.university.c.uniName,
                    schema.university.c.uniType,
                    schema.uniquestion.c.yID,
                )
                .order_by(func.max(schema.unisurvey.c.submittedAt).desc())
                .limit(recent_limit)
            )
            .mappings()
            .all()
        )

    year_meta = {
        row["yID"]: {
            "label": year_label(row["yearFrom"], row["yearTo"]),
            "question_count": question_counts[row["yID"]],
        }
        for row in year_rows
    }
    recent_reports = []
    for row in recent_rows:
        year_id = row["yID"]
        meta = year_meta.get(year_id, {})
        questions = int(meta.get("question_count") or 0)
        answered = int(row["answered_questions"] or 0)
        completion = _percent(answered, questions)
        recent_reports.append(
            {
                "university_id": row["uniId"],
                "university": row["uniName"],
                "university_type": row["uniType"],
                "year_id": year_id,
                "year_label": meta.get("label", "—"),
                "question_count": questions,
                "answered_questions": answered,
                "answer_rows": int(row["answer_rows"] or 0),
                "item_total": int(row["item_total"] or 0),
                "completion_percent": completion,
                "submitted_at": _iso(row["submitted_at"]),
                "status": "completed" if questions and answered >= questions else "in_progress",
            }
        )

    expected_reports = len(year_rows) * total_universities
    return {
        "totals": {
            "universities": total_universities,
            "active_years": len(year_rows),
            "questions": question_total,
            "reports_expected": expected_reports,
            "reports_submitted": report_total,
            "reports_pending": max(0, expected_reports - report_total),
            "participating_universities": participating,
            "completion_percent": _percent(report_total, expected_reports),
            "answer_coverage_percent": _percent(
                answer_total, expected_answers
            ),
            "answers": answer_total,
            "last_submitted_at": _iso(last_activity),
        },
        "active_years": active_years,
        "recent_reports": recent_reports,
    }

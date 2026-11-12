"""Read-only summaries for active university survey years.

The university survey stores one answer row per institution and question in
``unisurvey``. The reports page needs a year-level view of that data without
changing the native tables or the existing submission APIs.
"""

from sqlalchemy import func, select

from app.storage import university_survey_schema as schema

MONTH_NAMES = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def year_label(year_from, year_to):
    """Return the same readable period label used by the survey builder."""
    month = getattr(year_from, "month", 0)
    year = getattr(year_to, "year", None) or getattr(year_from, "year", None)
    if 1 <= month <= 12 and year:
        return f"{MONTH_NAMES[month]} {year}"
    if year:
        return str(year)
    return "ကာလ မသတ်မှတ်ထားပါ"


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

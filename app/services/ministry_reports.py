"""Read-only summaries for active ministry survey years.

The ministry survey mirrors the university survey: ``ministrysurvey`` stores
one answer row per ministry and question.  The reports pages need the same
year-level views as the university reports without exposing a ministry type
dimension.
"""

from sqlalchemy import and_, case, func, select

from app.services.university_reports import period_heading, year_label
from app.storage import ministry_survey_schema as schema


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


def ministry_year_roster(db, year_id, state):
    """Return the ministries that have or have not submitted for a year."""
    if state not in {"answered", "pending"}:
        raise ValueError("Unsupported ministry roster state.")

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
            select(func.count(schema.ministryquestion.c.mQId)).where(
                schema.ministryquestion.c.yID == year_id
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
                    schema.ministry.c.ministryId,
                    schema.ministry.c.ministryName,
                    func.count(
                        func.distinct(schema.ministrysurvey.c.mQId)
                    ).label("answered_questions"),
                    func.max(schema.ministrysurvey.c.submittedAt).label(
                        "last_submitted_at"
                    ),
                )
                .select_from(
                    schema.ministrysurvey.join(
                        schema.ministry,
                        schema.ministry.c.ministryId
                        == schema.ministrysurvey.c.ministryId,
                    ).join(
                        schema.ministryquestion,
                        schema.ministryquestion.c.mQId
                        == schema.ministrysurvey.c.mQId,
                    )
                )
                .where(schema.ministryquestion.c.yID == year_id)
                .group_by(
                    schema.ministry.c.ministryId,
                    schema.ministry.c.ministryName,
                )
                .order_by(
                    func.lower(schema.ministry.c.ministryName),
                    schema.ministry.c.ministryId,
                )
            )
            .mappings()
            .all()
        )
    else:
        has_answer = (
            select(schema.ministrysurvey.c.mSurveyId)
            .select_from(
                schema.ministrysurvey.join(
                    schema.ministryquestion,
                    schema.ministryquestion.c.mQId
                    == schema.ministrysurvey.c.mQId,
                )
            )
            .where(
                schema.ministrysurvey.c.ministryId
                == schema.ministry.c.ministryId,
                schema.ministryquestion.c.yID == year_id,
            )
        )
        roster = (
            connection.execute(
                select(
                    schema.ministry.c.ministryId,
                    schema.ministry.c.ministryName,
                )
                .where(~has_answer.exists())
                .order_by(
                    func.lower(schema.ministry.c.ministryName),
                    schema.ministry.c.ministryId,
                )
            )
            .mappings()
            .all()
        )

    ministries = []
    for row in roster:
        answered = int(row.get("answered_questions") or 0)
        completion = _percent(answered, question_count)
        ministries.append(
            {
                "ministry_id": row["ministryId"],
                "ministry": row["ministryName"],
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
        "total": len(ministries),
        "ministries": ministries,
    }


def ministry_answer_detail(db, year_id, ministry_id):
    """Return every ministry question for a year with one ministry's answer."""
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

    ministry_row = (
        connection.execute(
            select(
                schema.ministry.c.ministryId,
                schema.ministry.c.ministryName,
            ).where(schema.ministry.c.ministryId == ministry_id)
        )
        .mappings()
        .first()
    )
    if not ministry_row:
        return None

    rows = (
        connection.execute(
            select(
                schema.ministryquestion.c.mQId,
                schema.ministryquestion.c.mQDetail,
                schema.ministryquestion.c.qTID,
                schema.questiontitle.c.qTDetail,
                schema.questiontitle.c.description.label("title_description"),
                schema.ministrysurvey.c.mSurveyId,
                schema.ministrysurvey.c.hasItem,
                schema.ministrysurvey.c.itemCount,
                schema.ministrysurvey.c.surveyDescription,
                schema.ministrysurvey.c.remark,
                schema.ministrysurvey.c.submittedAt,
                schema.ministrysurvey.c.updatedAt,
            )
            .select_from(
                schema.ministryquestion
                .outerjoin(
                    schema.questiontitle,
                    schema.questiontitle.c.qTID
                    == schema.ministryquestion.c.qTID,
                )
                .outerjoin(
                    schema.ministrysurvey,
                    and_(
                        schema.ministrysurvey.c.mQId
                        == schema.ministryquestion.c.mQId,
                        schema.ministrysurvey.c.ministryId == ministry_id,
                    ),
                )
            )
            .where(schema.ministryquestion.c.yID == year_id)
            .order_by(
                schema.ministryquestion.c.qTID,
                schema.ministryquestion.c.mQId,
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
        answered = row["mSurveyId"] is not None
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
                "question_id": row["mQId"],
                "number": number,
                "question": row["mQDetail"],
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
        "ministry": {
            "ministry_id": ministry_row["ministryId"],
            "ministry": ministry_row["ministryName"],
        },
        "groups": groups,
    }


def ministry_question_answer_rates(db, year_id):
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

    total_ministries = (
        connection.execute(
            select(func.count()).select_from(schema.ministry)
        ).scalar()
        or 0
    )
    answered_ministries = (
        connection.execute(
            select(
                func.count(func.distinct(schema.ministrysurvey.c.ministryId))
            )
            .select_from(
                schema.ministrysurvey.join(
                    schema.ministryquestion,
                    schema.ministryquestion.c.mQId
                    == schema.ministrysurvey.c.mQId,
                )
            )
            .where(schema.ministryquestion.c.yID == year_id)
        ).scalar()
        or 0
    )

    answered_count = func.count(
        func.distinct(schema.ministrysurvey.c.ministryId)
    ).label("answered_ministries")
    has_item_count = func.count(
        func.distinct(
            case(
                (
                    schema.ministrysurvey.c.hasItem.is_(True),
                    schema.ministrysurvey.c.ministryId,
                )
            )
        )
    ).label("has_item_count")
    no_item_count = func.count(
        func.distinct(
            case(
                (
                    schema.ministrysurvey.c.hasItem.is_(False),
                    schema.ministrysurvey.c.ministryId,
                )
            )
        )
    ).label("no_item_count")

    rows = (
        connection.execute(
            select(
                schema.ministryquestion.c.mQId,
                schema.ministryquestion.c.mQDetail,
                schema.ministryquestion.c.qTID,
                schema.questiontitle.c.qTDetail,
                schema.questiontitle.c.description.label("title_description"),
                answered_count,
                has_item_count,
                no_item_count,
            )
            .select_from(
                schema.ministryquestion
                .outerjoin(
                    schema.questiontitle,
                    schema.questiontitle.c.qTID
                    == schema.ministryquestion.c.qTID,
                )
                .outerjoin(
                    schema.ministrysurvey,
                    schema.ministrysurvey.c.mQId
                    == schema.ministryquestion.c.mQId,
                )
            )
            .where(schema.ministryquestion.c.yID == year_id)
            .group_by(
                schema.ministryquestion.c.mQId,
                schema.ministryquestion.c.mQDetail,
                schema.ministryquestion.c.qTID,
                schema.questiontitle.c.qTDetail,
                schema.questiontitle.c.description,
            )
            .order_by(
                schema.ministryquestion.c.qTID,
                schema.ministryquestion.c.mQId,
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
        question_answered = int(row["answered_ministries"] or 0)
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
                "question_id": row["mQId"],
                "number": number,
                "question": row["mQDetail"],
                "answered_ministries": question_answered,
                "unanswered_ministries": max(
                    0, total_ministries - question_answered
                ),
                "has_item_count": has_items,
                "no_item_count": no_items,
                "has_item_percent": _percent(has_items, question_answered),
                "no_item_percent": _percent(no_items, question_answered),
                "answered_percent": _percent(
                    question_answered, total_ministries
                ),
            }
        )

    not_answered = max(0, total_ministries - answered_ministries)
    return {
        "year_id": year_row["yID"],
        "year_label": year_label(
            year_row["yearFrom"], year_row["yearTo"]
        ),
        "year_from": getattr(year_row["yearFrom"], "year", None),
        "year_to": getattr(year_row["yearTo"], "year", None),
        "question_count": len(rows),
        "total_ministries": total_ministries,
        "answered_ministries": answered_ministries,
        "not_answered_ministries": not_answered,
        "answered_percent": _percent(
            answered_ministries, total_ministries
        ),
        "not_answered_percent": _percent(
            not_answered, total_ministries
        ),
        "groups": groups,
    }


def ministry_activity(db, recent_limit=8):
    """Build the ministry activity contract consumed by the reports page."""
    connection = db.native

    total_ministries = (
        connection.execute(
            select(func.count()).select_from(schema.ministry)
        ).scalar()
        or 0
    )

    year_rows = (
        connection.execute(
            select(
                schema.year.c.yID,
                schema.year.c.yearFrom,
                schema.year.c.yearTo,
                func.count(schema.ministryquestion.c.mQId).label(
                    "question_count"
                ),
            )
            .join(
                schema.ministryquestion,
                schema.ministryquestion.c.yID == schema.year.c.yID,
            )
            .where(schema.year.c.status == 1)
            .group_by(
                schema.year.c.yID,
                schema.year.c.yearFrom,
                schema.year.c.yearTo,
            )
            .order_by(
                func.coalesce(
                    schema.year.c.yearTo, schema.year.c.yearFrom
                ).desc(),
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
                    schema.ministryquestion.c.yID,
                    func.count(
                        func.distinct(schema.ministrysurvey.c.ministryId)
                    ).label("submitted_ministries"),
                    func.count(
                        func.distinct(schema.ministrysurvey.c.mQId)
                    ).label("answered_questions"),
                    func.count(schema.ministrysurvey.c.mSurveyId).label(
                        "answer_rows"
                    ),
                    func.max(schema.ministrysurvey.c.submittedAt).label(
                        "last_submitted_at"
                    ),
                    func.sum(
                        func.coalesce(schema.ministrysurvey.c.itemCount, 0)
                    ).label("item_total"),
                )
                .select_from(
                    schema.ministryquestion.outerjoin(
                        schema.ministrysurvey,
                        schema.ministrysurvey.c.mQId
                        == schema.ministryquestion.c.mQId,
                    )
                )
                .where(schema.ministryquestion.c.yID.in_(year_ids))
                .group_by(schema.ministryquestion.c.yID)
            )
            .mappings()
            .all()
        )
        stats_by_year = {row["yID"]: row for row in stats}

    question_counts = {
        row["yID"]: int(row["question_count"] or 0)
        for row in year_rows
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
        submitted = int(stats.get("submitted_ministries") or 0)
        answer_rows = int(stats.get("answer_rows") or 0)
        completion = _percent(submitted, total_ministries)
        coverage = _percent(
            answer_rows, total_ministries * questions
        )
        pending = max(0, total_ministries - submitted)
        last_submitted = stats.get("last_submitted_at")
        active_years.append(
            {
                "year_id": year_id,
                "label": year_label(row["yearFrom"], row["yearTo"]),
                "year_from": getattr(row["yearFrom"], "year", None),
                "year_to": getattr(row["yearTo"], "year", None),
                "question_count": questions,
                "submitted_ministries": submitted,
                "pending_ministries": pending,
                "completion_percent": completion,
                "answer_coverage_percent": coverage,
                "answer_rows": answer_rows,
                "item_total": int(stats.get("item_total") or 0),
                "last_submitted_at": _iso(last_submitted),
                "status": _year_status(
                    submitted, total_ministries, completion
                ),
            }
        )
        report_total += submitted
        answer_total += answer_rows
        question_total += questions
        expected_answers += total_ministries * questions
        if last_submitted and (
            last_activity is None or last_submitted > last_activity
        ):
            last_activity = last_submitted

    participating = 0
    if year_ids:
        participating = (
            connection.execute(
                select(
                    func.count(
                        func.distinct(schema.ministrysurvey.c.ministryId)
                    )
                )
                .select_from(
                    schema.ministrysurvey.join(
                        schema.ministryquestion,
                        schema.ministryquestion.c.mQId
                        == schema.ministrysurvey.c.mQId,
                    )
                )
                .where(schema.ministryquestion.c.yID.in_(year_ids))
            ).scalar()
            or 0
        )

    recent_rows = []
    if year_ids:
        recent_rows = (
            connection.execute(
                select(
                    schema.ministry.c.ministryId,
                    schema.ministry.c.ministryName,
                    schema.ministryquestion.c.yID,
                    func.count(
                        func.distinct(schema.ministrysurvey.c.mQId)
                    ).label("answered_questions"),
                    func.count(schema.ministrysurvey.c.mSurveyId).label(
                        "answer_rows"
                    ),
                    func.max(schema.ministrysurvey.c.submittedAt).label(
                        "submitted_at"
                    ),
                    func.sum(
                        func.coalesce(schema.ministrysurvey.c.itemCount, 0)
                    ).label("item_total"),
                )
                .select_from(
                    schema.ministrysurvey.join(
                        schema.ministry,
                        schema.ministry.c.ministryId
                        == schema.ministrysurvey.c.ministryId,
                    )
                    .join(
                        schema.ministryquestion,
                        schema.ministryquestion.c.mQId
                        == schema.ministrysurvey.c.mQId,
                    )
                    .join(
                        schema.year,
                        schema.year.c.yID
                        == schema.ministryquestion.c.yID,
                    )
                )
                .where(schema.year.c.status == 1)
                .group_by(
                    schema.ministry.c.ministryId,
                    schema.ministry.c.ministryName,
                    schema.ministryquestion.c.yID,
                )
                .order_by(
                    func.max(schema.ministrysurvey.c.submittedAt).desc()
                )
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
                "ministry_id": row["ministryId"],
                "ministry": row["ministryName"],
                "year_id": year_id,
                "year_label": meta.get("label", "—"),
                "question_count": questions,
                "answered_questions": answered,
                "answer_rows": int(row["answer_rows"] or 0),
                "item_total": int(row["item_total"] or 0),
                "completion_percent": completion,
                "submitted_at": _iso(row["submitted_at"]),
                "status": (
                    "completed"
                    if questions and answered >= questions
                    else "in_progress"
                ),
            }
        )

    expected_reports = len(year_rows) * total_ministries
    return {
        "totals": {
            "ministries": total_ministries,
            "active_years": len(year_rows),
            "questions": question_total,
            "reports_expected": expected_reports,
            "reports_submitted": report_total,
            "reports_pending": max(0, expected_reports - report_total),
            "participating_ministries": participating,
            "completion_percent": _percent(
                report_total, expected_reports
            ),
            "answer_coverage_percent": _percent(
                answer_total, expected_answers
            ),
            "answers": answer_total,
            "last_submitted_at": _iso(last_activity),
        },
        "active_years": active_years,
        "recent_reports": recent_reports,
    }

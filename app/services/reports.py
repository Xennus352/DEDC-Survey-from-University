"""Database-backed reporting; list and export share the same filtered query."""

from datetime import datetime, timedelta, timezone
import math
from sqlalchemy import Float, String, cast, extract, func, select
from app.models.forms import (
    AuditLog,
    FieldAnswer,
    FormField,
    FormVersion,
    Submission,
    SurveyForm,
    WorkbookAnswer,
    WorkbookImport,
    AnswerFile,
)
from app.storage import schema
from app.storage.compact import envelope
from app.storage.existing import metadata as existing_metadata
from app.services.presentation import answer_text, value_text
from app.models.user import User


def completed_survey_answers_by_year(db):
    """Count submitted question answers by calendar year of submission.

    Native survey rows have no completion flag: each persisted row is one
    submitted answer. Include the last four years even when a year has zero
    answers, plus any older years present in the database.
    """
    current_year = datetime.now().year
    years = set(range(current_year - 3, current_year + 1))
    results = {}
    for audience, survey, organization, org_key, label_column in (
        ("university", schema.unisurvey, schema.university, "uniId", "uniType"),
        ("ministry", schema.ministrysurvey, schema.ministry, "ministryId", "ministryName"),
    ):
        labels = [row[0] for row in db.native.execute(
            select(organization.c[label_column]).distinct().order_by(organization.c[label_column])
        )]
        year_column = extract("year", survey.c.submittedAt)
        answer_source = survey.join(
            organization, survey.c[org_key] == organization.c[org_key]
        )
        totals = {}
        for label, year, total in db.native.execute(
            select(organization.c[label_column], year_column, func.count())
            .select_from(answer_source)
            .group_by(organization.c[label_column], year_column)
        ):
            if year:
                year = int(year)
                years.add(year)
                key = (label, year)
                totals[key] = totals.get(key, 0) + total
        results[audience] = (labels, totals)

    ordered_years = sorted(years)
    return {
        "years": ordered_years,
        **{
            audience: {
                "series": [
                    {
                        "label": label,
                        "values": [totals.get((label, year), 0) for year in ordered_years],
                    }
                    for label in labels
                ]
            }
            for audience, (labels, totals) in results.items()
        },
    }


def overview(db):
    count = lambda model: db.query(func.count()).select_from(model).scalar() or 0
    native_count = lambda table: db.native.execute(
        select(func.count()).select_from(table)
    ).scalar() or 0

    native_year = existing_metadata.tables["year"]

    def native_question_count(table):
        if db.layout:
            return db.native.execute(
                select(func.count())
                .select_from(table.join(native_year, table.c.yID == native_year.c.yID))
                .where(native_year.c.status == 1)
            ).scalar() or 0
        return sum(
            (envelope(description) or {}).get("kind") != "metadata"
            for description, in db.native.execute(select(table.c.description))
        )

    completed_by_year = completed_survey_answers_by_year(db)

    since = datetime.now(timezone.utc).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=29)
    trends = (
        db.query(func.date(Submission.created_at), func.count())
        .filter(Submission.created_at >= since)
        .group_by(func.date(Submission.created_at))
        .all()
    )
    dates = {str(day): total for day, total in trends}
    answer_dates = {}
    for audience, table in (("university", schema.unisurvey), ("ministry", schema.ministrysurvey)):
        daily_counts = db.native.execute(
            select(func.date(table.c.submittedAt), func.count())
            .where(table.c.submittedAt >= since)
            .group_by(func.date(table.c.submittedAt))
        )
        answer_dates[audience] = {str(day): total for day, total in daily_counts}
    published_forms = db.query(SurveyForm.id).filter(
        SurveyForm.archived.is_(False),
        SurveyForm.id.in_(
            db.query(FormVersion.form_id).filter_by(status="published").distinct()
        ),
    )
    archived_forms = db.query(SurveyForm).filter_by(archived=True).count()
    published_form_count = published_forms.count()
    total_forms = count(SurveyForm)
    form_status = {
        "published": published_form_count,
        "draft": max(total_forms - archived_forms - published_form_count, 0),
        "archived": archived_forms,
    }
    if db.layout:
        # The forms page lists each audience/year pair with questions as a survey.
        form_status = {"published": 0, "draft": 0, "archived": 0}
        for table_name in ("uniquestion", "ministryquestion"):
            question_table = existing_metadata.tables[table_name]
            states = db.native.execute(
                select(native_year.c.status, func.count(func.distinct(question_table.c.yID)))
                .select_from(question_table.join(native_year, question_table.c.yID == native_year.c.yID))
                .group_by(native_year.c.status)
            )
            for status, total in states:
                form_status["published" if status == 1 else "draft"] += total

        # Native public surveys store one row per question. Count one submission
        # per organization, survey year, and day; app-owned rows have a remark.
        for survey_name, question_name, org_column, question_column in (
            ("unisurvey", "uniquestion", "uniId", "uQId"),
            ("ministrysurvey", "ministryquestion", "ministryId", "mQId"),
        ):
            survey_table = existing_metadata.tables[survey_name]
            question_table = existing_metadata.tables[question_name]
            native_days = db.native.execute(
                select(
                    func.date(survey_table.c.submittedAt),
                    survey_table.c[org_column],
                    question_table.c.yID,
                )
                .select_from(survey_table.join(
                    question_table,
                    survey_table.c[question_column] == question_table.c[question_column],
                ))
                .where(survey_table.c.submittedAt >= since, survey_table.c.remark.is_(None))
                .distinct()
            )
            for day, _, _ in native_days:
                key = str(day)
                dates[key] = dates.get(key, 0) + 1
    submission_statuses = dict(
        db.query(Submission.status, func.count()).group_by(Submission.status).all()
    )
    total_submissions = sum(submission_statuses.values())
    approved_submissions = submission_statuses.get("approved", 0)
    rejected_submissions = submission_statuses.get("rejected", 0)
    pending_submissions = submission_statuses.get("pending_review", 0)
    return {
        "forms": total_forms,
        "form_status": form_status,
        "published": db.query(FormVersion).filter_by(status="published").count(),
        "questions": db.query(
            FormField.version_id,
            func.coalesce(
                FormField.config["source_cell"].as_string(), cast(FormField.id, String)
            ),
        )
        .distinct()
        .count(),
        "answer_fields": count(FormField),
        "submissions": total_submissions,
        "pending_review": pending_submissions,
        "collection_status": {
            "approved": approved_submissions,
            "pending": pending_submissions,
            "rejected": rejected_submissions,
        },
        "source_rows": count(WorkbookAnswer),
        "directory_stats": {
            "university_questions": native_question_count(
                existing_metadata.tables["uniquestion"] if db.layout else schema.uniquestion
            ),
            "ministry_questions": native_question_count(
                existing_metadata.tables["ministryquestion"] if db.layout else schema.ministryquestion
            ),
            "universities": native_count(schema.university),
            "ministries": native_count(schema.ministry),
        },
        "completed_by_year": completed_by_year,
        "users": count(User),
        "active_users": db.query(User).filter_by(is_active=True).count(),
        "trend": [
            {
                "date": (since + timedelta(days=i)).date().isoformat(),
                "count": dates.get((since + timedelta(days=i)).date().isoformat(), 0),
            }
            for i in range(30)
        ],
        "answer_trend": [
            {
                "date": (since + timedelta(days=i)).date().isoformat(),
                "university": answer_dates["university"].get(
                    (since + timedelta(days=i)).date().isoformat(), 0
                ),
                "ministry": answer_dates["ministry"].get(
                    (since + timedelta(days=i)).date().isoformat(), 0
                ),
            }
            for i in range(30)
        ],
    }


def filtered_submissions(
    db,
    search="",
    form_id=None,
    version_id=None,
    status=None,
    user_id=None,
    start=None,
    end=None,
    question=None,
    operator="equals",
    answer=None,
):
    query = (
        db.query(Submission)
        .join(FormVersion)
        .join(SurveyForm)
        .join(User, User.id == Submission.user_id)
    )
    if search:
        query = query.filter(
            SurveyForm.title.contains(search) | User.username.contains(search)
        )
    if form_id:
        query = query.filter(FormVersion.form_id == form_id)
    if version_id:
        query = query.filter(Submission.version_id == version_id)
    if status:
        query = query.filter(Submission.status == status)
    if user_id:
        query = query.filter(Submission.user_id == user_id)
    if start:
        query = query.filter(
            Submission.created_at >= datetime.combine(start, datetime.min.time())
        )
    if end:
        query = query.filter(
            Submission.created_at <= datetime.combine(end, datetime.max.time())
        )
    if question and answer is not None:
        if operator in {"greater_than", "less_than"} and not math.isfinite(
            float(answer)
        ):
            raise ValueError("Numeric filters require a finite number.")
        answers = (
            db.query(FieldAnswer.submission_id)
            .join(FormField, FormField.id == FieldAnswer.field_id)
            .filter(FormField.key == question)
        )
        if operator == "greater_than":
            answers = answers.filter(cast(FieldAnswer.value, Float) > float(answer))
        elif operator == "less_than":
            answers = answers.filter(cast(FieldAnswer.value, Float) < float(answer))
        elif operator == "contains":
            answers = answers.filter(cast(FieldAnswer.value, String).contains(answer))
        else:
            answers = answers.filter(FieldAnswer.value == json_value(answer))
        query = query.filter(Submission.id.in_(answers))
    return query


def json_value(answer):
    import json

    try:
        return json.loads(answer)
    except (ValueError, TypeError):
        return answer


def submission_row(db, row):
    account = db.get(User, row.user_id)
    return {
        "id": row.id,
        "form": row.version.title,
        "form_id": row.version.form_id,
        "version": row.version.number,
        "version_id": row.version_id,
        "reporting_start": row.reporting_start.isoformat()
        if row.reporting_start
        else None,
        "reporting_end": row.reporting_end.isoformat() if row.reporting_end else None,
        "username": account.username if account else "Deleted account",
        "status": row.status,
        "created_at": row.created_at.isoformat(),
        "location": row.location,
    }


def submission_detail(db, row):
    result = submission_row(db, row)
    values = {a.field_id: a.value for a in row.answers}
    def display(question):
        value = values.get(question.id)
        attachment = db.get(AnswerFile, value['file_id']) if question.kind in {'file', 'image'} and isinstance(value, dict) and value.get('file_id') else None
        return answer_text(question, value, attachment.filename if attachment else None)
    result["sections"] = [
        {
            "title": s.title,
            "answers": [
                {
                    "key": q.key,
                    "title": q.title,
                    "kind": q.kind,
                    "value": values.get(q.id),
                    "display_value": display(q),
                }
                for q in s.questions
            ],
        }
        for s in row.version.sections
    ]
    return result


def analytics(db, query, question=None):
    from sqlalchemy import text

    total = query.count()
    completed = query.filter(Submission.completed_at.is_not(None)).count()
    if db.bind.dialect.name == "mysql":
        elapsed = func.timestampdiff(
            text("SECOND"), Submission.started_at, Submission.completed_at
        )
    else:
        elapsed = (
            func.julianday(Submission.completed_at)
            - func.julianday(Submission.started_at)
        ) * 86400
    average = (
        query.filter(
            Submission.started_at.is_not(None), Submission.completed_at.is_not(None)
        )
        .with_entities(func.avg(elapsed))
        .scalar()
    )
    daily = (
        query.with_entities(func.date(Submission.created_at), func.count())
        .group_by(func.date(Submission.created_at))
        .order_by(func.date(Submission.created_at).desc())
        .limit(366)
        .all()
    )
    people = (
        query.with_entities(User.username, func.count())
        .group_by(User.username)
        .order_by(func.count().desc())
        .limit(20)
        .all()
    )
    distribution = []
    if question:
        definitions = db.query(FormField).filter(
            FormField.key == question,
            FormField.version_id.in_(query.with_entities(Submission.version_id)),
        ).all()

        def distribution_text(value):
            labels = {answer_text(field, value) for field in definitions}
            if len(labels) == 1:
                return labels.pop()
            return value_text(value) + (' (labels vary by version)' if labels else '')

        answers = (
            db.query(FieldAnswer.value, func.count())
            .join(FormField, FormField.id == FieldAnswer.field_id)
            .filter(
                FormField.key == question,
                FieldAnswer.submission_id.in_(query.with_entities(Submission.id)),
            )
        )
        distribution = [
            {"answer": value, "display_value": distribution_text(value), "count": count}
            for value, count in answers.group_by(FieldAnswer.value)
            .order_by(func.count().desc())
            .limit(20)
        ]
    return {
        "completion_percent": round(completed * 100 / total, 1) if total else 0,
        "average_seconds": round(float(average), 1) if average is not None else None,
        "trend": [{"date": str(day), "count": count} for day, count in reversed(daily)],
        "by_user": [{"username": name, "count": count} for name, count in people],
        "question_distribution": distribution,
    }

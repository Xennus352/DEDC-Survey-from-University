"""Database operations for the public university survey."""
from sqlalchemy import exists, func, select

from app.storage import university_survey_schema as survey_schema


def active_years(connection):
    """Return active years that contain at least one university question."""
    question_count = func.count(survey_schema.uniquestion.c.uQId).label(
        "questionCount"
    )
    statement = (
        select(
            survey_schema.year.c.yID,
            survey_schema.year.c.yearFrom,
            survey_schema.year.c.yearTo,
            question_count,
        )
        .join(
            survey_schema.uniquestion,
            survey_schema.uniquestion.c.yID == survey_schema.year.c.yID,
        )
        .where(survey_schema.year.c.status == 1)
        .group_by(
            survey_schema.year.c.yID,
            survey_schema.year.c.yearFrom,
            survey_schema.year.c.yearTo,
        )
        .order_by(
            func.coalesce(
                survey_schema.year.c.yearFrom,
                survey_schema.year.c.yearTo,
            ).desc(),
            survey_schema.year.c.yID.desc(),
        )
    )
    return [dict(row) for row in connection.execute(statement).mappings()]


def active_year(connection, year_id):
    statement = select(
        survey_schema.year.c.yID,
        survey_schema.year.c.yearFrom,
        survey_schema.year.c.yearTo,
    ).where(
        survey_schema.year.c.yID == year_id,
        survey_schema.year.c.status == 1,
        exists().where(
            survey_schema.uniquestion.c.yID == survey_schema.year.c.yID
        ),
    )
    row = connection.execute(statement).mappings().first()
    return dict(row) if row else None


def questions_for_year(connection, year_id):
    statement = (
        select(
            survey_schema.uniquestion.c.uQId,
            survey_schema.uniquestion.c.uQDetail,
            survey_schema.uniquestion.c.qTID,
            survey_schema.questiontitle.c.qTDetail,
            survey_schema.questiontitle.c.description.label("titleDescription"),
        )
        .select_from(
            survey_schema.uniquestion.outerjoin(
                survey_schema.questiontitle,
                survey_schema.uniquestion.c.qTID
                == survey_schema.questiontitle.c.qTID,
            )
        )
        .where(survey_schema.uniquestion.c.yID == year_id)
        .order_by(
            survey_schema.uniquestion.c.qTID,
            survey_schema.uniquestion.c.uQId,
        )
    )
    return [dict(row) for row in connection.execute(statement).mappings()]


def universities(connection):
    statement = select(
        survey_schema.university.c.uniId,
        survey_schema.university.c.uniType,
        survey_schema.university.c.uniName,
    ).order_by(
        survey_schema.university.c.uniName,
        survey_schema.university.c.uniId,
    )
    return [dict(row) for row in connection.execute(statement).mappings()]


def university(connection, university_id):
    statement = select(
        survey_schema.university.c.uniId,
        survey_schema.university.c.uniType,
        survey_schema.university.c.uniName,
    ).where(survey_schema.university.c.uniId == university_id)
    row = connection.execute(statement).mappings().first()
    return dict(row) if row else None


def save_answers(connection, university_id, questions, answers):
    """Insert one row per unanswered question and skip existing submissions."""
    question_ids = [question["uQId"] for question in questions]
    if not question_ids:
        return 0, 0

    submitted = set(
        connection.execute(
            select(survey_schema.unisurvey.c.uQId).where(
                survey_schema.unisurvey.c.uniId == university_id,
                survey_schema.unisurvey.c.uQId.in_(question_ids),
            )
        ).scalars()
    )

    saved = 0
    skipped = 0
    for question in questions:
        question_id = question["uQId"]
        if question_id in submitted:
            skipped += 1
            continue
        answer = answers[question_id]
        connection.execute(
            survey_schema.unisurvey.insert().values(
                uniId=university_id,
                uQId=question_id,
                hasItem=answer["has_item"],
                itemCount=answer["item_count"],
                surveyDescription=answer["survey_description"],
                remark=None,
            )
        )
        saved += 1

    return saved, skipped

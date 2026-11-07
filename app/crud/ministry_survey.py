"""Database operations for the public ministry survey."""
from sqlalchemy import exists, func, select

from app.storage import ministry_survey_schema as survey_schema


def active_years(connection):
    """Return active years that contain at least one ministry question."""
    question_count = func.count(survey_schema.ministryquestion.c.mQId).label(
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
            survey_schema.ministryquestion,
            survey_schema.ministryquestion.c.yID
            == survey_schema.year.c.yID,
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
            survey_schema.ministryquestion.c.yID
            == survey_schema.year.c.yID
        ),
    )
    row = connection.execute(statement).mappings().first()
    return dict(row) if row else None


def questions_for_year(connection, year_id):
    statement = (
        select(
            survey_schema.ministryquestion.c.mQId,
            survey_schema.ministryquestion.c.mQDetail,
            survey_schema.ministryquestion.c.qTID,
            survey_schema.questiontitle.c.qTDetail,
            survey_schema.questiontitle.c.description.label("titleDescription"),
        )
        .select_from(
            survey_schema.ministryquestion.outerjoin(
                survey_schema.questiontitle,
                survey_schema.ministryquestion.c.qTID
                == survey_schema.questiontitle.c.qTID,
            )
        )
        .where(survey_schema.ministryquestion.c.yID == year_id)
        .order_by(
            survey_schema.ministryquestion.c.qTID,
            survey_schema.ministryquestion.c.mQId,
        )
    )
    return [dict(row) for row in connection.execute(statement).mappings()]


def ministries(connection):
    statement = select(
        survey_schema.ministry.c.ministryId,
        survey_schema.ministry.c.ministryName,
    ).order_by(
        survey_schema.ministry.c.ministryName,
        survey_schema.ministry.c.ministryId,
    )
    return [dict(row) for row in connection.execute(statement).mappings()]


def save_answers(connection, ministry_id, questions, answers):
    """Insert one row per unanswered question and skip existing submissions."""
    question_ids = [question["mQId"] for question in questions]
    if not question_ids:
        return 0, 0

    submitted = set(
        connection.execute(
            select(survey_schema.ministrysurvey.c.mQId).where(
                survey_schema.ministrysurvey.c.ministryId == ministry_id,
                survey_schema.ministrysurvey.c.mQId.in_(question_ids),
            )
        ).scalars()
    )

    saved = 0
    skipped = 0
    for question in questions:
        question_id = question["mQId"]
        if question_id in submitted:
            skipped += 1
            continue
        answer = answers[question_id]
        connection.execute(
            survey_schema.ministrysurvey.insert().values(
                ministryId=ministry_id,
                mQId=question_id,
                hasItem=answer["has_item"],
                itemCount=answer["item_count"],
                surveyDescription=answer["survey_description"],
                remark=None,
            )
        )
        saved += 1

    return saved, skipped

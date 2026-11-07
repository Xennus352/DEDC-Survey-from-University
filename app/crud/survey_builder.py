"""Database operations for the admin survey form builder.

Uses ONLY the 10 existing tables from dedc.sql with SQLAlchemy Core and native connections.
"""
from datetime import date, datetime
from typing import Any
from sqlalchemy import String, cast, func, select, update, delete, text
from sqlalchemy.orm import Session

from app.storage import university_survey_schema as uni_schema
from app.storage import ministry_survey_schema as min_schema
from app.models.native_forms import Year, QuestionTitle, UniQuestion, MinistryQuestion, University, Ministry, UniSurvey, MinistrySurvey
from app.schemas.survey_builder import (
    YearInput,
    YearOutput,
    QuestionTitleInput,
    QuestionTitleOutput,
    UniQuestionInput,
    UniQuestionOutput,
    MinistryQuestionInput,
    MinistryQuestionOutput,
    OrgType,
    SurveyFormVirtual,
    SurveyFormWithQuestions,
    SurveyListParams,
    YearListParams,
    QuestionListParams,
)


# Helper functions for date/year extraction
def _extract_year(val) -> int:
    """Extract year from various formats (date, string, int)."""
    if val is None:
        return 0
    if hasattr(val, 'year'):
        return val.year
    if isinstance(val, str):
        try:
            from datetime import date
            return date.fromisoformat(val).year
        except ValueError:
            try:
                return int(val)
            except ValueError:
                return 0
    if isinstance(val, int):
        return val
    return 0


def _extract_month(val) -> int:
    """Extract month from various formats (date, string, int)."""
    if val is None:
        return 0
    if hasattr(val, 'month'):
        return val.month
    if isinstance(val, str):
        try:
            from datetime import date
            return date.fromisoformat(val).month
        except ValueError:
            try:
                return int(val)
            except ValueError:
                return 0
    if isinstance(val, int):
        return val
    return 0


def _get_native_connection(db: Session):
    """Get the native SQLAlchemy connection from the session."""
    return db.native


# ============================================================
# Year CRUD (uses `year` table via Core)
# ============================================================

def create_year(db: Session, data: YearInput) -> Year:
    """Create a new year period in `year` table."""
    conn = _get_native_connection(db)
    result = conn.execute(
        uni_schema.year.insert().values(
            yID=max(conn.execute(select(func.max(uni_schema.year.c.yID))).scalar() or 0, 0) + 1,
            yearFrom=date(data.year_to, data.year_from, 1),
            yearTo=date(data.year_to, data.year_from, 1),
            status=data.status,
        )
    )
    yID = result.inserted_primary_key[0]
    return conn.execute(select(uni_schema.year).where(uni_schema.year.c.yID == yID)).first()


def get_year(db: Session, yID: int) -> Any:
    """Get a year by ID from `year` table."""
    conn = _get_native_connection(db)
    return conn.execute(select(uni_schema.year).where(uni_schema.year.c.yID == yID)).first()


def update_year(db: Session, yID: int, data: YearInput) -> Any:
    """Update a year period in `year` table."""
    conn = _get_native_connection(db)
    conn.execute(
        uni_schema.year.update()
        .where(uni_schema.year.c.yID == yID)
        .values(yearFrom=date(data.year_to, data.year_from, 1), yearTo=date(data.year_to, data.year_from, 1), status=data.status)
    )
    return conn.execute(select(uni_schema.year).where(uni_schema.year.c.yID == yID)).first()


def delete_year(db: Session, yID: int) -> bool:
    """Delete a year period from `year` table (only if no questions reference it)."""
    conn = _get_native_connection(db)

    # Check for referencing questions
    uni_count = conn.execute(
        select(func.count(uni_schema.uniquestion.c.uQId)).where(uni_schema.uniquestion.c.yID == yID)
    ).scalar()
    min_count = conn.execute(
        select(func.count(min_schema.ministryquestion.c.mQId)).where(min_schema.ministryquestion.c.yID == yID)
    ).scalar()

    if uni_count > 0 or min_count > 0:
        raise ValueError(f"Cannot delete year: {uni_count} university questions and {min_count} ministry questions reference it")

    conn.execute(uni_schema.year.delete().where(uni_schema.year.c.yID == yID))
    return True


def list_years(db: Session, params: YearListParams) -> tuple[list[YearOutput], int]:
    """List year periods from `year` table with pagination."""
    conn = _get_native_connection(db)
    query = select(uni_schema.year).where(uni_schema.year.c.yID > 0)
    if params.search:
        query = query.where(cast(uni_schema.year.c.yearTo, String).contains(params.search))

    if params.status is not None:
        query = query.where(uni_schema.year.c.status == params.status)

    total = conn.execute(select(func.count()).select_from(query.subquery())).scalar()

    years = conn.execute(
        query.order_by(uni_schema.year.c.yearTo.desc(), uni_schema.year.c.yearFrom.desc(), uni_schema.year.c.yID.desc())
        .offset((params.page - 1) * params.limit)
        .limit(params.limit)
    ).all()

    results = []
    month_names = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    for y in years:
        month_from = _extract_month(y.yearFrom)
        year_from = _extract_year(y.yearFrom)
        year_to = _extract_year(y.yearTo)

        month = month_names[month_from] if 1 <= month_from <= 12 else "Unknown"
        label = f"{month} {year_to}" if year_to else f"Month {month_from} Year {year_from}"
        results.append(YearOutput(
            yID=y.yID,
            year_from=month_from,
            year_to=year_to,
            status=y.status,
            label=label,
        ))

    return results, total


def get_active_years(db: Session) -> list[YearOutput]:
    """Get all published years (status=1) that have questions in `uniquestion` or `ministryquestion`."""
    conn = _get_native_connection(db)

    # Years with uni questions
    uni_years = conn.execute(
        select(uni_schema.year)
        .join(uni_schema.uniquestion, uni_schema.uniquestion.c.yID == uni_schema.year.c.yID)
        .where(uni_schema.year.c.status == 1)
        .distinct()
    ).all()

    # Years with ministry questions
    min_years = conn.execute(
        select(uni_schema.year)
        .join(min_schema.ministryquestion, min_schema.ministryquestion.c.yID == uni_schema.year.c.yID)
        .where(uni_schema.year.c.status == 1)
        .distinct()
    ).all()

    # Combine and deduplicate
    seen = set()
    results = []
    month_names = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    for y in uni_years + min_years:
        if y.yID not in seen:
            seen.add(y.yID)
            month_from = _extract_month(y.yearFrom)
            year_from = _extract_year(y.yearFrom)
            year_to = _extract_year(y.yearTo)

            month = month_names[month_from] if 1 <= month_from <= 12 else "Unknown"
            label = f"{month} {year_to}" if year_to else f"Month {month_from} Year {year_from}"
            results.append(YearOutput(
                yID=y.yID,
                year_from=month_from,
                year_to=year_to,
                status=y.status,
                label=label,
            ))

    return sorted(results, key=lambda x: (x.year_to, x.year_from), reverse=True)


# ============================================================
# QuestionTitle CRUD (uses `questiontitle` table via Core)
# ============================================================

def create_question_title(db: Session, data: QuestionTitleInput) -> Any:
    """Create a new question title in `questiontitle` table."""
    conn = _get_native_connection(db)
    result = conn.execute(
        uni_schema.questiontitle.insert().values(
            qTID=max(conn.execute(select(func.max(uni_schema.questiontitle.c.qTID))).scalar() or 0, 0) + 1,
            qTDetail=data.qTDetail,
            description=data.description,
        )
    )
    qTID = result.inserted_primary_key[0]
    return conn.execute(select(uni_schema.questiontitle).where(uni_schema.questiontitle.c.qTID == qTID)).first()


def get_question_title(db: Session, qTID: int) -> Any:
    """Get a question title by ID from `questiontitle` table."""
    conn = _get_native_connection(db)
    return conn.execute(select(uni_schema.questiontitle).where(uni_schema.questiontitle.c.qTID == qTID)).first()


def update_question_title(db: Session, qTID: int, data: QuestionTitleInput) -> Any:
    """Update a question title in `questiontitle` table."""
    conn = _get_native_connection(db)
    conn.execute(
        uni_schema.questiontitle.update()
        .where(uni_schema.questiontitle.c.qTID == qTID)
        .values(qTDetail=data.qTDetail, description=data.description)
    )
    return conn.execute(select(uni_schema.questiontitle).where(uni_schema.questiontitle.c.qTID == qTID)).first()


def delete_question_title(db: Session, qTID: int) -> bool:
    """Delete a question title from `questiontitle` table (only if no questions reference it)."""
    conn = _get_native_connection(db)

    uni_count = conn.execute(
        select(func.count(uni_schema.uniquestion.c.uQId)).where(uni_schema.uniquestion.c.qTID == qTID)
    ).scalar()
    min_count = conn.execute(
        select(func.count(min_schema.ministryquestion.c.mQId)).where(min_schema.ministryquestion.c.qTID == qTID)
    ).scalar()

    if uni_count > 0 or min_count > 0:
        raise ValueError(f"Cannot delete title: {uni_count} university questions and {min_count} ministry questions reference it")

    conn.execute(uni_schema.questiontitle.delete().where(uni_schema.questiontitle.c.qTID == qTID))
    return True


def list_question_titles(db: Session, params: QuestionListParams) -> tuple[list[QuestionTitleOutput], int]:
    """List question titles from `questiontitle` table with pagination."""
    conn = _get_native_connection(db)
    query = select(uni_schema.questiontitle).where(uni_schema.questiontitle.c.qTID > 0)

    if params.search:
        query = query.where(uni_schema.questiontitle.c.qTDetail.contains(params.search))

    if params.title_id:
        query = query.where(uni_schema.questiontitle.c.qTID == params.title_id)

    total = conn.execute(select(func.count()).select_from(query.subquery())).scalar()

    titles = conn.execute(
        query.order_by(uni_schema.questiontitle.c.qTID.desc())
        .offset((params.page - 1) * params.limit)
        .limit(params.limit)
    ).all()

    results = [QuestionTitleOutput(
        qTID=t.qTID,
        qTDetail=t.qTDetail,
        description=t.description,
    ) for t in titles]

    return results, total


def get_all_question_titles(db: Session) -> list[QuestionTitleOutput]:
    """Get all question titles from `questiontitle` table for dropdowns."""
    conn = _get_native_connection(db)
    titles = conn.execute(
        select(uni_schema.questiontitle).where(uni_schema.questiontitle.c.qTID > 0).order_by(uni_schema.questiontitle.c.qTDetail)
    ).all()
    return [QuestionTitleOutput(
        qTID=t.qTID,
        qTDetail=t.qTDetail,
        description=t.description,
    ) for t in titles]


# ============================================================
# UniQuestion CRUD (uses `uniquestion` table via Core)
# ============================================================

def create_uni_question(db: Session, data: UniQuestionInput) -> Any:
    """Create a new university question in `uniquestion` table."""
    conn = _get_native_connection(db)
    # Verify year exists
    year = conn.execute(select(uni_schema.year).where(uni_schema.year.c.yID == data.yID)).first()
    if not year:
        raise ValueError(f"Year {data.yID} not found")

    # Verify question title exists if provided
    if data.qTID:
        title = conn.execute(select(uni_schema.questiontitle).where(uni_schema.questiontitle.c.qTID == data.qTID)).first()
        if not title:
            raise ValueError(f"Question title {data.qTID} not found")

    result = conn.execute(
        uni_schema.uniquestion.insert().values(
            uQDetail=data.uQDetail,
            qTID=data.qTID,
            yID=data.yID,
        )
    )
    uQId = result.inserted_primary_key[0]
    return conn.execute(select(uni_schema.uniquestion).where(uni_schema.uniquestion.c.uQId == uQId)).first()


def get_uni_question(db: Session, uQId: int) -> Any:
    """Get a university question by ID from `uniquestion` table."""
    conn = _get_native_connection(db)
    return conn.execute(select(uni_schema.uniquestion).where(uni_schema.uniquestion.c.uQId == uQId)).first()


def update_uni_question(db: Session, uQId: int, data: UniQuestionInput) -> Any:
    """Update a university question in `uniquestion` table."""
    conn = _get_native_connection(db)
    year = conn.execute(select(uni_schema.year).where(uni_schema.year.c.yID == data.yID)).first()
    if not year:
        raise ValueError(f"Year {data.yID} not found")

    if data.qTID:
        title = conn.execute(select(uni_schema.questiontitle).where(uni_schema.questiontitle.c.qTID == data.qTID)).first()
        if not title:
            raise ValueError(f"Question title {data.qTID} not found")

    conn.execute(
        uni_schema.uniquestion.update()
        .where(uni_schema.uniquestion.c.uQId == uQId)
        .values(uQDetail=data.uQDetail, qTID=data.qTID, yID=data.yID)
    )
    return conn.execute(select(uni_schema.uniquestion).where(uni_schema.uniquestion.c.uQId == uQId)).first()


def delete_uni_question(db: Session, uQId: int) -> bool:
    """Delete a university question from `uniquestion` table (only if no survey responses in `unisurvey` reference it)."""
    conn = _get_native_connection(db)

    survey_count = conn.execute(
        select(func.count(uni_schema.unisurvey.c.uniSurveyId)).where(uni_schema.unisurvey.c.uQId == uQId)
    ).scalar()

    if survey_count > 0:
        raise ValueError(f"Cannot delete question: {survey_count} survey responses in `unisurvey` reference it")

    conn.execute(uni_schema.uniquestion.delete().where(uni_schema.uniquestion.c.uQId == uQId))
    return True


def list_uni_questions(db: Session, params: QuestionListParams) -> tuple[list[UniQuestionOutput], int]:
    """List university questions from `uniquestion` table with pagination."""
    conn = _get_native_connection(db)
    query = select(
        uni_schema.uniquestion.c.uQId,
        uni_schema.uniquestion.c.uQDetail,
        uni_schema.uniquestion.c.qTID,
        uni_schema.uniquestion.c.yID,
        uni_schema.questiontitle.c.qTDetail,
        uni_schema.questiontitle.c.description.label("titleDescription"),
    ).select_from(
        uni_schema.uniquestion.outerjoin(
            uni_schema.questiontitle,
            uni_schema.uniquestion.c.qTID == uni_schema.questiontitle.c.qTID,
        )
    )

    if params.search:
        query = query.where(
            uni_schema.uniquestion.c.uQDetail.contains(params.search) |
            uni_schema.questiontitle.c.qTDetail.contains(params.search)
        )

    if params.year_id:
        query = query.where(uni_schema.uniquestion.c.yID == params.year_id)

    if params.title_id:
        query = query.where(uni_schema.uniquestion.c.qTID == params.title_id)

    total = conn.execute(select(func.count()).select_from(query.subquery())).scalar()

    questions = conn.execute(
        query.order_by(uni_schema.uniquestion.c.qTID, uni_schema.uniquestion.c.uQId)
        .offset((params.page - 1) * params.limit)
        .limit(params.limit)
    ).all()

    results = []
    for q in questions:
        results.append(UniQuestionOutput(
            uQId=q.uQId,
            uQDetail=q.uQDetail,
            qTID=q.qTID,
            yID=q.yID,
            qTDetail=q.qTDetail,
            title_description=q.titleDescription,
        ))

    return results, total


def get_uni_questions_by_year(db: Session, year_id: int) -> list[UniQuestionOutput]:
    """Get all university questions for a specific year from `uniquestion` table, grouped by title."""
    conn = _get_native_connection(db)
    questions = conn.execute(
        select(
            uni_schema.uniquestion.c.uQId,
            uni_schema.uniquestion.c.uQDetail,
            uni_schema.uniquestion.c.qTID,
            uni_schema.uniquestion.c.yID,
            uni_schema.questiontitle.c.qTDetail,
            uni_schema.questiontitle.c.description.label("titleDescription"),
        )
        .select_from(
            uni_schema.uniquestion.outerjoin(
                uni_schema.questiontitle,
                uni_schema.uniquestion.c.qTID == uni_schema.questiontitle.c.qTID,
            )
        )
        .where(uni_schema.uniquestion.c.yID == year_id)
        .order_by(uni_schema.uniquestion.c.qTID, uni_schema.uniquestion.c.uQId)
    ).all()

    results = []
    for q in questions:
        results.append(UniQuestionOutput(
            uQId=q.uQId,
            uQDetail=q.uQDetail,
            qTID=q.qTID,
            yID=q.yID,
            qTDetail=q.qTDetail,
            title_description=q.titleDescription,
        ))

    return results


# ============================================================
# MinistryQuestion CRUD (uses `ministryquestion` table via Core)
# ============================================================

def create_ministry_question(db: Session, data: MinistryQuestionInput) -> Any:
    """Create a new ministry question in `ministryquestion` table."""
    conn = _get_native_connection(db)
    year = conn.execute(select(uni_schema.year).where(uni_schema.year.c.yID == data.yID)).first()
    if not year:
        raise ValueError(f"Year {data.yID} not found")

    if data.qTID:
        title = conn.execute(select(uni_schema.questiontitle).where(uni_schema.questiontitle.c.qTID == data.qTID)).first()
        if not title:
            raise ValueError(f"Question title {data.qTID} not found")

    result = conn.execute(
        min_schema.ministryquestion.insert().values(
            mQDetail=data.mQDetail,
            qTID=data.qTID,
            yID=data.yID,
        )
    )
    mQId = result.inserted_primary_key[0]
    return conn.execute(select(min_schema.ministryquestion).where(min_schema.ministryquestion.c.mQId == mQId)).first()


def get_ministry_question(db: Session, mQId: int) -> Any:
    """Get a ministry question by ID from `ministryquestion` table."""
    conn = _get_native_connection(db)
    return conn.execute(select(min_schema.ministryquestion).where(min_schema.ministryquestion.c.mQId == mQId)).first()


def update_ministry_question(db: Session, mQId: int, data: MinistryQuestionInput) -> Any:
    """Update a ministry question in `ministryquestion` table."""
    conn = _get_native_connection(db)
    year = conn.execute(select(uni_schema.year).where(uni_schema.year.c.yID == data.yID)).first()
    if not year:
        raise ValueError(f"Year {data.yID} not found")

    if data.qTID:
        title = conn.execute(select(uni_schema.questiontitle).where(uni_schema.questiontitle.c.qTID == data.qTID)).first()
        if not title:
            raise ValueError(f"Question title {data.qTID} not found")

    conn.execute(
        min_schema.ministryquestion.update()
        .where(min_schema.ministryquestion.c.mQId == mQId)
        .values(mQDetail=data.mQDetail, qTID=data.qTID, yID=data.yID)
    )
    return conn.execute(select(min_schema.ministryquestion).where(min_schema.ministryquestion.c.mQId == mQId)).first()


def delete_ministry_question(db: Session, mQId: int) -> bool:
    """Delete a ministry question from `ministryquestion` table (only if no survey responses in `ministrysurvey` reference it)."""
    conn = _get_native_connection(db)

    survey_count = conn.execute(
        select(func.count(min_schema.ministrysurvey.c.mSurveyId)).where(min_schema.ministrysurvey.c.mQId == mQId)
    ).scalar()

    if survey_count > 0:
        raise ValueError(f"Cannot delete question: {survey_count} survey responses in `ministrysurvey` reference it")

    conn.execute(min_schema.ministryquestion.delete().where(min_schema.ministryquestion.c.mQId == mQId))
    return True


def list_ministry_questions(db: Session, params: QuestionListParams) -> tuple[list[MinistryQuestionOutput], int]:
    """List ministry questions from `ministryquestion` table with pagination."""
    conn = _get_native_connection(db)
    query = select(
        min_schema.ministryquestion.c.mQId,
        min_schema.ministryquestion.c.mQDetail,
        min_schema.ministryquestion.c.qTID,
        min_schema.ministryquestion.c.yID,
        uni_schema.questiontitle.c.qTDetail,
        uni_schema.questiontitle.c.description.label("titleDescription"),
    ).select_from(
        min_schema.ministryquestion.outerjoin(
            uni_schema.questiontitle,
            min_schema.ministryquestion.c.qTID == uni_schema.questiontitle.c.qTID,
        )
    )

    if params.search:
        query = query.where(
            min_schema.ministryquestion.c.mQDetail.contains(params.search) |
            uni_schema.questiontitle.c.qTDetail.contains(params.search)
        )

    if params.year_id:
        query = query.where(min_schema.ministryquestion.c.yID == params.year_id)

    if params.title_id:
        query = query.where(min_schema.ministryquestion.c.qTID == params.title_id)

    total = conn.execute(select(func.count()).select_from(query.subquery())).scalar()

    questions = conn.execute(
        query.order_by(min_schema.ministryquestion.c.qTID, min_schema.ministryquestion.c.mQId)
        .offset((params.page - 1) * params.limit)
        .limit(params.limit)
    ).all()

    results = []
    for q in questions:
        results.append(MinistryQuestionOutput(
            mQId=q.mQId,
            mQDetail=q.mQDetail,
            qTID=q.qTID,
            yID=q.yID,
            qTDetail=q.qTDetail,
            title_description=q.titleDescription,
        ))

    return results, total


def get_ministry_questions_by_year(db: Session, year_id: int) -> list[MinistryQuestionOutput]:
    """Get all ministry questions for a specific year from `ministryquestion` table, grouped by title."""
    conn = _get_native_connection(db)
    questions = conn.execute(
        select(
            min_schema.ministryquestion.c.mQId,
            min_schema.ministryquestion.c.mQDetail,
            min_schema.ministryquestion.c.qTID,
            min_schema.ministryquestion.c.yID,
            uni_schema.questiontitle.c.qTDetail,
            uni_schema.questiontitle.c.description.label("titleDescription"),
        )
        .select_from(
            min_schema.ministryquestion.outerjoin(
                uni_schema.questiontitle,
                min_schema.ministryquestion.c.qTID == uni_schema.questiontitle.c.qTID,
            )
        )
        .where(min_schema.ministryquestion.c.yID == year_id)
        .order_by(min_schema.ministryquestion.c.qTID, min_schema.ministryquestion.c.mQId)
    ).all()

    results = []
    for q in questions:
        results.append(MinistryQuestionOutput(
            mQId=q.mQId,
            mQDetail=q.mQDetail,
            qTID=q.qTID,
            yID=q.yID,
            qTDetail=q.qTDetail,
            title_description=q.titleDescription,
        ))

    return results


# ============================================================
# Organizations (uses `university` and `ministry` tables via Core)
# ============================================================

def get_universities(db: Session) -> list[dict[str, Any]]:
    """Get all universities from `university` table for dropdowns."""
    conn = _get_native_connection(db)
    unis = conn.execute(
        select(uni_schema.university.c.uniId, uni_schema.university.c.uniName, uni_schema.university.c.uniType)
        .order_by(uni_schema.university.c.uniName)
    ).all()
    return [{"id": u.uniId, "name": u.uniName, "type": u.uniType} for u in unis]


def get_ministries(db: Session) -> list[dict[str, Any]]:
    """Get all ministries from `ministry` table for dropdowns."""
    conn = _get_native_connection(db)
    mins = conn.execute(
        select(min_schema.ministry.c.ministryId, min_schema.ministry.c.ministryName)
        .order_by(min_schema.ministry.c.ministryName)
    ).all()
    return [{"id": m.ministryId, "name": m.ministryName, "type": "ministry"} for m in mins]


def get_organizations(db: Session, org_type: OrgType) -> list[dict[str, Any]]:
    """Get organizations by type from `university` or `ministry` table."""
    if org_type == "university":
        return get_universities(db)
    return get_ministries(db)


# ============================================================
# Bulk Operations for Excel Import (uses existing tables only)
# ============================================================

def bulk_create_question_titles(db: Session, titles: list[dict[str, Any]]) -> dict[int, int]:
    """Bulk create question titles in `questiontitle` table, return mapping of temp_id -> real_qTID."""
    conn = _get_native_connection(db)
    mapping = {}
    for i, title_data in enumerate(titles):
        result = conn.execute(
            uni_schema.questiontitle.insert().values(
                qTDetail=title_data.get("qTDetail", ""),
                description=title_data.get("description"),
            )
        )
        mapping[i] = result.inserted_primary_key[0]
    return mapping


def bulk_create_uni_questions(db: Session, questions: list[dict[str, Any]], title_mapping: dict[int, int]) -> list[int]:
    """Bulk create university questions in `uniquestion` table, return list of created uQIds."""
    conn = _get_native_connection(db)
    created_ids = []
    for q_data in questions:
        qTID = q_data.get("qTID")
        if qTID is not None and qTID in title_mapping:
            qTID = title_mapping[qTID]

        result = conn.execute(
            uni_schema.uniquestion.insert().values(
                uQDetail=q_data.get("uQDetail", ""),
                qTID=qTID,
                yID=q_data.get("yID"),
            )
        )
        created_ids.append(result.inserted_primary_key[0])
    return created_ids


def bulk_create_ministry_questions(db: Session, questions: list[dict[str, Any]], title_mapping: dict[int, int]) -> list[int]:
    """Bulk create ministry questions in `ministryquestion` table, return list of created mQIds."""
    conn = _get_native_connection(db)
    created_ids = []
    for q_data in questions:
        qTID = q_data.get("qTID")
        if qTID is not None and qTID in title_mapping:
            qTID = title_mapping[qTID]

        result = conn.execute(
            min_schema.ministryquestion.insert().values(
                mQDetail=q_data.get("mQDetail", ""),
                qTID=qTID,
                yID=q_data.get("yID"),
            )
        )
        created_ids.append(result.inserted_primary_key[0])
    return created_ids


def find_or_create_question_title(db: Session, qTDetail: str, description: str | None = None) -> Any:
    """Find existing question title in `questiontitle` table or create new one."""
    conn = _get_native_connection(db)
    existing = conn.execute(
        select(uni_schema.questiontitle).where(uni_schema.questiontitle.c.qTDetail == qTDetail)
    ).first()
    if existing:
        return existing
    result = conn.execute(
        uni_schema.questiontitle.insert().values(qTDetail=qTDetail, description=description)
    )
    qTID = result.inserted_primary_key[0]
    return conn.execute(select(uni_schema.questiontitle).where(uni_schema.questiontitle.c.qTID == qTID)).first()


def find_or_create_uni_question(db: Session, uQDetail: str, yID: int, qTID: int | None = None) -> Any:
    """Find existing university question in `uniquestion` table or create new one."""
    conn = _get_native_connection(db)
    existing = conn.execute(
        select(uni_schema.uniquestion).where(
            uni_schema.uniquestion.c.uQDetail == uQDetail,
            uni_schema.uniquestion.c.yID == yID
        )
    ).first()
    if existing:
        return existing
    result = conn.execute(
        uni_schema.uniquestion.insert().values(uQDetail=uQDetail, yID=yID, qTID=qTID)
    )
    uQId = result.inserted_primary_key[0]
    return conn.execute(select(uni_schema.uniquestion).where(uni_schema.uniquestion.c.uQId == uQId)).first()


def find_or_create_ministry_question(db: Session, mQDetail: str, yID: int, qTID: int | None = None) -> Any:
    """Find existing ministry question in `ministryquestion` table or create new one."""
    conn = _get_native_connection(db)
    existing = conn.execute(
        select(min_schema.ministryquestion).where(
            min_schema.ministryquestion.c.mQDetail == mQDetail,
            min_schema.ministryquestion.c.yID == yID
        )
    ).first()
    if existing:
        return existing
    result = conn.execute(
        min_schema.ministryquestion.insert().values(mQDetail=mQDetail, yID=yID, qTID=qTID)
    )
    mQId = result.inserted_primary_key[0]
    return conn.execute(select(min_schema.ministryquestion).where(min_schema.ministryquestion.c.mQId == mQId)).first()


# ============================================================
# Virtual Survey Forms (NO new table - defined by year + org_type)
# ============================================================

def get_virtual_survey_forms(db: Session, params: SurveyListParams) -> tuple[list[SurveyFormVirtual], int]:
    """Get virtual survey forms (combinations of year + org_type that have questions)."""
    conn = _get_native_connection(db)
    forms = []

    # Get years with university questions
    if params.org_type in (None, "university"):
        uni_years = conn.execute(
            select(uni_schema.year.c.yID, uni_schema.year.c.yearFrom, uni_schema.year.c.yearTo, uni_schema.year.c.status)
            .join(uni_schema.uniquestion, uni_schema.uniquestion.c.yID == uni_schema.year.c.yID)
            .distinct()
        ).all()
        for y in uni_years:
            if params.year_id and y.yID != params.year_id:
                continue
            if params.is_active is not None and (y.status == 1) != params.is_active:
                continue

            q_count = conn.execute(
                select(func.count(uni_schema.uniquestion.c.uQId)).where(uni_schema.uniquestion.c.yID == y.yID)
            ).scalar()

            month_names = [
                "", "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ]
            month_from = _extract_month(y.yearFrom)
            year_from = _extract_year(y.yearFrom)
            year_to = _extract_year(y.yearTo)
            month = month_names[month_from] if 1 <= month_from <= 12 else "Unknown"
            label = f"{month} {year_to}" if year_to else f"Month {month_from} Year {year_from}"

            forms.append(SurveyFormVirtual(
                year_id=y.yID,
                year_label=label,
                org_type="university",
                title=f"University Survey {label}",
                description=None,
                is_active=y.status == 1,
                question_count=q_count or 0,
            ))

    # Get years with ministry questions
    if params.org_type in (None, "ministry"):
        min_years = conn.execute(
            select(uni_schema.year.c.yID, uni_schema.year.c.yearFrom, uni_schema.year.c.yearTo, uni_schema.year.c.status)
            .join(min_schema.ministryquestion, min_schema.ministryquestion.c.yID == uni_schema.year.c.yID)
            .distinct()
        ).all()
        for y in min_years:
            if params.year_id and y.yID != params.year_id:
                continue
            if params.is_active is not None and (y.status == 1) != params.is_active:
                continue

            q_count = conn.execute(
                select(func.count(min_schema.ministryquestion.c.mQId)).where(min_schema.ministryquestion.c.yID == y.yID)
            ).scalar()

            month_names = [
                "", "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ]
            month_from = _extract_month(y.yearFrom)
            year_from = _extract_year(y.yearFrom)
            year_to = _extract_year(y.yearTo)
            month = month_names[month_from] if 1 <= month_from <= 12 else "Unknown"
            label = f"{month} {year_to}" if year_to else f"Month {month_from} Year {year_from}"

            forms.append(SurveyFormVirtual(
                year_id=y.yID,
                year_label=label,
                org_type="ministry",
                title=f"Ministry Survey {label}",
                description=None,
                is_active=y.status == 1,
                question_count=q_count or 0,
            ))

    # Filter by search
    if params.search:
        forms = [f for f in forms if params.search.lower() in f.title.lower() or params.search.lower() in f.year_label.lower()]

    # Sort by year desc, org_type
    forms.sort(key=lambda f: (f.year_id, f.org_type), reverse=True)

    total = len(forms)
    start = (params.page - 1) * params.limit
    end = start + params.limit

    return forms[start:end], total


def get_survey_builder_data(db: Session, org_type: OrgType, year_id: int) -> SurveyFormWithQuestions | None:
    """Get all data needed for the survey form builder (virtual form)."""
    conn = _get_native_connection(db)
    year = conn.execute(select(uni_schema.year).where(uni_schema.year.c.yID == year_id)).first()
    if not year:
        return None

    if org_type == "university":
        questions = get_uni_questions_by_year(db, year_id)
        organizations = get_universities(db)
    else:
        questions = get_ministry_questions_by_year(db, year_id)
        organizations = get_ministries(db)

    titles = get_all_question_titles(db)
    years = get_active_years(db)

    month_names = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    month_from = _extract_month(year.yearFrom)
    year_from = _extract_year(year.yearFrom)
    year_to = _extract_year(year.yearTo)
    month = month_names[month_from] if 1 <= month_from <= 12 else "Unknown"
    label = f"{month} {year_to}" if year_to else f"Month {month_from} Year {year_from}"

    form = SurveyFormVirtual(
        year_id=year_id,
        year_label=label,
        org_type=org_type,
        title=f"{org_type.title()} Survey {label}",
        description=None,
        is_active=year.status == 1,
        question_count=len(questions),
    )

    # Convert questions to link format (virtual - no table)
    question_links = []
    for i, q in enumerate(questions):
        if org_type == "university":
            question_links.append({
                "id": q.uQId,
                "question_id": q.uQId,
                "question_type": "uniquestion",
                "display_order": i,
                "is_required": True,
                "question_detail": q.uQDetail,
                "question_title": q.qTDetail,
            })
        else:
            question_links.append({
                "id": q.mQId,
                "question_id": q.mQId,
                "question_type": "ministryquestion",
                "display_order": i,
                "is_required": True,
                "question_detail": q.mQDetail,
                "question_title": q.qTDetail,
            })

    return SurveyFormWithQuestions(
        form=form,
        questions=question_links,
        available_questions=questions,
        available_titles=titles,
        years=years,
        organizations=organizations,
    )

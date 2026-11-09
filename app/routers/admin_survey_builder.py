"""Admin routes for the survey form builder - using ONLY existing 10 tables."""
import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.admin_auth import AdminIdentity, require_admin
from app.crud import survey_builder as crud
from app.crud.survey_builder import _extract_year, _extract_month
from app.dependencies import get_db
from app.schemas.survey_builder import (
    BulkQuestionCreate,
    ExcelImportConfirm,
    ExcelImportPreview,
    MinistryQuestionInput,
    MinistryQuestionOutput,
    OrgType,
    QuestionListParams,
    QuestionTitleInput,
    QuestionTitleOutput,
    ReorderQuestionsRequest,
    SurveyFormVirtual,
    SurveyFormWithQuestions,
    SurveyListParams,
    UniQuestionInput,
    UniQuestionOutput,
    YearInput,
    YearListParams,
    YearOutput,
)

router = APIRouter(prefix="/api/admin/survey", tags=["survey builder"])


# ============================================================
# Year Management (uses `year` table)
# ============================================================

@router.get("/years", response_model=list[YearOutput])
def list_years(
    params: YearListParams = Depends(),
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """List all year periods from `year` table with pagination."""
    years, total = crud.list_years(db, params)
    return years


@router.get("/years/active", response_model=list[YearOutput])
def get_active_years(
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Get all published years (status=1) that have questions in `uniquestion` or `ministryquestion`."""
    return crud.get_active_years(db)


@router.get("/years/{yID}", response_model=YearOutput)
def get_year(
    yID: int,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Get a year by ID from `year` table."""
    year = crud.get_year(db, yID)
    if not year:
        raise HTTPException(404, "Year not found")
    
    month_names = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    month_from = _extract_month(year.yearFrom)
    year_from = _extract_year(year.yearFrom)
    year_to = _extract_year(year.yearTo)
    
    month = month_names[month_from] if 1 <= month_from <= 12 else "Unknown"
    label = f"{month} {year_to}" if year_to else f"Month {month_from} Year {year_from}"
    
    return YearOutput(
        yID=year.yID,
        year_from=month_from,
        year_to=year_to,
        status=year.status,
        label=label,
    )


@router.post("/years", response_model=YearOutput, status_code=201)
def create_year(
    data: YearInput,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Create a new year period in `year` table."""
    year = crud.create_year(db, data)
    db.commit()
    
    month_names = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    month_from = _extract_month(year.yearFrom)
    year_from = _extract_year(year.yearFrom)
    year_to = _extract_year(year.yearTo)
    
    month = month_names[month_from] if 1 <= month_from <= 12 else "Unknown"
    label = f"{month} {year_to}" if year_to else f"Month {month_from} Year {year_from}"
    
    return YearOutput(
        yID=year.yID,
        year_from=month_from,
        year_to=year_to,
        status=year.status,
        label=label,
    )


@router.put("/years/{yID}", response_model=YearOutput)
def update_year(
    yID: int,
    data: YearInput,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Update a year period in `year` table."""
    year = crud.update_year(db, yID, data)
    if not year:
        raise HTTPException(404, "Year not found")
    db.commit()
    
    month_names = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    month_from = _extract_month(year.yearFrom)
    year_from = _extract_year(year.yearFrom)
    year_to = _extract_year(year.yearTo)
    
    month = month_names[month_from] if 1 <= month_from <= 12 else "Unknown"
    label = f"{month} {year_to}" if year_to else f"Month {month_from} Year {year_from}"
    
    return YearOutput(
        yID=year.yID,
        year_from=month_from,
        year_to=year_to,
        status=year.status,
        label=label,
    )


@router.delete("/years/{yID}", status_code=204)
def delete_year(
    yID: int,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Delete a year period from `year` table."""
    try:
        result = crud.delete_year(db, yID)
        if not result:
            raise HTTPException(404, "Year not found")
        db.commit()
    except ValueError as e:
        raise HTTPException(409, str(e))


# ============================================================
# Question Title Management (uses `questiontitle` table)
# ============================================================

@router.get("/question-titles", response_model=list[QuestionTitleOutput])
def list_question_titles(
    params: QuestionListParams = Depends(),
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """List all question titles from `questiontitle` table with pagination."""
    titles, total = crud.list_question_titles(db, params)
    return titles


@router.get("/question-titles/all", response_model=list[QuestionTitleOutput])
def get_all_question_titles(
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Get all question titles from `questiontitle` table for dropdowns."""
    return crud.get_all_question_titles(db)


@router.get("/question-titles/{qTID}", response_model=QuestionTitleOutput)
def get_question_title(
    qTID: int,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Get a question title by ID from `questiontitle` table."""
    title = crud.get_question_title(db, qTID)
    if not title:
        raise HTTPException(404, "Question title not found")
    return QuestionTitleOutput(
        qTID=title.qTID,
        qTDetail=title.qTDetail,
        description=title.description,
    )


@router.post("/question-titles", response_model=QuestionTitleOutput, status_code=201)
def create_question_title(
    data: QuestionTitleInput,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Create a new question title in `questiontitle` table."""
    title = crud.create_question_title(db, data)
    db.commit()
    return QuestionTitleOutput(
        qTID=title.qTID,
        qTDetail=title.qTDetail,
        description=title.description,
    )


@router.put("/question-titles/{qTID}", response_model=QuestionTitleOutput)
def update_question_title(
    qTID: int,
    data: QuestionTitleInput,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Update a question title in `questiontitle` table."""
    title = crud.update_question_title(db, qTID, data)
    if not title:
        raise HTTPException(404, "Question title not found")
    db.commit()
    return QuestionTitleOutput(
        qTID=title.qTID,
        qTDetail=title.qTDetail,
        description=title.description,
    )


@router.delete("/question-titles/{qTID}", status_code=204)
def delete_question_title(
    qTID: int,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Delete a question title from `questiontitle` table."""
    try:
        result = crud.delete_question_title(db, qTID)
        if not result:
            raise HTTPException(404, "Question title not found")
        db.commit()
    except ValueError as e:
        raise HTTPException(409, str(e))


# ============================================================
# University Question Management (uses `uniquestion` table)
# ============================================================

@router.get("/questions/university", response_model=list[UniQuestionOutput])
def list_uni_questions(
    params: QuestionListParams = Depends(),
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """List university questions from `uniquestion` table with pagination."""
    questions, total = crud.list_uni_questions(db, params)
    return questions


@router.get("/questions/university/by-year/{year_id}", response_model=list[UniQuestionOutput])
def get_uni_questions_by_year(
    year_id: int,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Get all university questions for a specific year from `uniquestion` table."""
    year = crud.get_year(db, year_id)
    if not year:
        raise HTTPException(404, "Year not found")
    return crud.get_uni_questions_by_year(db, year_id)


@router.get("/questions/university/{uQId}", response_model=UniQuestionOutput)
def get_uni_question(
    uQId: int,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Get a university question by ID from `uniquestion` table."""
    question = crud.get_uni_question(db, uQId)
    if not question:
        raise HTTPException(404, "Question not found")
    
    title = crud.get_question_title(db, question.qTID) if question.qTID else None
    return UniQuestionOutput(
        uQId=question.uQId,
        uQDetail=question.uQDetail,
        qTID=question.qTID,
        yID=question.yID,
        qTDetail=title.qTDetail if title else None,
        title_description=title.description if title else None,
    )


@router.post("/questions/university", response_model=UniQuestionOutput, status_code=201)
def create_uni_question(
    data: UniQuestionInput,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Create a new university question in `uniquestion` table."""
    try:
        question = crud.create_uni_question(db, data)
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))
    
    title = crud.get_question_title(db, question.qTID) if question.qTID else None
    return UniQuestionOutput(
        uQId=question.uQId,
        uQDetail=question.uQDetail,
        qTID=question.qTID,
        yID=question.yID,
        qTDetail=title.qTDetail if title else None,
        title_description=title.description if title else None,
    )


@router.put("/questions/university/{uQId}", response_model=UniQuestionOutput)
def update_uni_question(
    uQId: int,
    data: UniQuestionInput,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Update a university question in `uniquestion` table."""
    try:
        question = crud.update_uni_question(db, uQId, data)
        if not question:
            raise HTTPException(404, "Question not found")
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))
    
    title = crud.get_question_title(db, question.qTID) if question.qTID else None
    return UniQuestionOutput(
        uQId=question.uQId,
        uQDetail=question.uQDetail,
        qTID=question.qTID,
        yID=question.yID,
        qTDetail=title.qTDetail if title else None,
        title_description=title.description if title else None,
    )


@router.delete("/questions/university/{uQId}", status_code=204)
def delete_uni_question(
    uQId: int,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Delete a university question from `uniquestion` table."""
    try:
        result = crud.delete_uni_question(db, uQId)
        if not result:
            raise HTTPException(404, "Question not found")
        db.commit()
    except ValueError as e:
        raise HTTPException(409, str(e))


# ============================================================
# Ministry Question Management (uses `ministryquestion` table)
# ============================================================

@router.get("/questions/ministry", response_model=list[MinistryQuestionOutput])
def list_ministry_questions(
    params: QuestionListParams = Depends(),
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """List ministry questions from `ministryquestion` table with pagination."""
    questions, total = crud.list_ministry_questions(db, params)
    return questions


@router.get("/questions/ministry/by-year/{year_id}", response_model=list[MinistryQuestionOutput])
def get_ministry_questions_by_year(
    year_id: int,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Get all ministry questions for a specific year from `ministryquestion` table."""
    year = crud.get_year(db, year_id)
    if not year:
        raise HTTPException(404, "Year not found")
    return crud.get_ministry_questions_by_year(db, year_id)


@router.get("/questions/ministry/{mQId}", response_model=MinistryQuestionOutput)
def get_ministry_question(
    mQId: int,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Get a ministry question by ID from `ministryquestion` table."""
    question = crud.get_ministry_question(db, mQId)
    if not question:
        raise HTTPException(404, "Question not found")
    
    title = crud.get_question_title(db, question.qTID) if question.qTID else None
    return MinistryQuestionOutput(
        mQId=question.mQId,
        mQDetail=question.mQDetail,
        qTID=question.qTID,
        yID=question.yID,
        qTDetail=title.qTDetail if title else None,
        title_description=title.description if title else None,
    )


@router.post("/questions/ministry", response_model=MinistryQuestionOutput, status_code=201)
def create_ministry_question(
    data: MinistryQuestionInput,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Create a new ministry question in `ministryquestion` table."""
    try:
        question = crud.create_ministry_question(db, data)
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))
    
    title = crud.get_question_title(db, question.qTID) if question.qTID else None
    return MinistryQuestionOutput(
        mQId=question.mQId,
        mQDetail=question.mQDetail,
        qTID=question.qTID,
        yID=question.yID,
        qTDetail=title.qTDetail if title else None,
        title_description=title.description if title else None,
    )


@router.put("/questions/ministry/{mQId}", response_model=MinistryQuestionOutput)
def update_ministry_question(
    mQId: int,
    data: MinistryQuestionInput,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Update a ministry question in `ministryquestion` table."""
    try:
        question = crud.update_ministry_question(db, mQId, data)
        if not question:
            raise HTTPException(404, "Question not found")
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))
    
    title = crud.get_question_title(db, question.qTID) if question.qTID else None
    return MinistryQuestionOutput(
        mQId=question.mQId,
        mQDetail=question.mQDetail,
        qTID=question.qTID,
        yID=question.yID,
        qTDetail=title.qTDetail if title else None,
        title_description=title.description if title else None,
    )


@router.delete("/questions/ministry/{mQId}", status_code=204)
def delete_ministry_question(
    mQId: int,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Delete a ministry question from `ministryquestion` table."""
    try:
        result = crud.delete_ministry_question(db, mQId)
        if not result:
            raise HTTPException(404, "Question not found")
        db.commit()
    except ValueError as e:
        raise HTTPException(409, str(e))


# ============================================================
# Organizations (uses `university` and `ministry` tables)
# ============================================================

@router.get("/organizations/{org_type}")
def get_organizations(
    org_type: OrgType,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Get organizations by type from `university` or `ministry` table."""
    orgs = crud.get_organizations(db, org_type)
    return {"items": orgs}


# ============================================================
# Excel Import (uses existing tables only)
# ============================================================

def parse_excel_file(file_content: bytes) -> tuple[list[str], list[list[Any]]]:
    """Parse Excel file content (supports CSV and Excel)."""
    # Try to parse as CSV first
    try:
        text = file_content.decode("utf-8")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if rows:
            return rows[0], rows[1:]
    except UnicodeDecodeError:
        pass
    
    # Try openpyxl for .xlsx files
    try:
        import openpyxl
        workbook = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True)
        sheet = workbook.active
        rows = []
        for row in sheet.iter_rows(values_only=True):
            rows.append(list(row))
        if rows:
            return rows[0], rows[1:]
    except ImportError:
        raise HTTPException(500, "openpyxl not installed for Excel parsing")
    except Exception as e:
        raise HTTPException(400, f"Failed to parse Excel file: {str(e)}")
    
    return [], []


def detect_org_type_and_year(headers: list[str], rows: list[list[Any]]) -> tuple[OrgType | None, int | None]:
    """Detect organization type and year from Excel data."""
    headers_lower = [h.lower().strip() for h in headers]
    
    uni_indicators = ["university", "uni", "uni_id", "uniid", "uni_name", "uniname", "uni_type", "unitype"]
    min_indicators = ["ministry", "ministry_id", "ministryid", "ministry_name", "ministryname"]
    
    org_type = None
    for h in headers_lower:
        if any(ind in h for ind in uni_indicators):
            org_type = "university"
            break
        if any(ind in h for ind in min_indicators):
            org_type = "ministry"
            break
    
    year_indicators = ["year", "yid", "y_id", "year_id", "yearid"]
    year_id = None
    for h in headers_lower:
        if any(ind in h for ind in year_indicators):
            col_idx = headers_lower.index(h)
            for row in rows[:5]:
                if col_idx < len(row):
                    try:
                        year_id = int(row[col_idx])
                        break
                    except (ValueError, TypeError):
                        continue
            break
    
    return org_type, year_id


def suggest_column_mapping(headers: list[str], org_type: OrgType) -> dict[str, str]:
    """Suggest column mapping based on headers."""
    mapping = {}
    headers_lower = [h.lower().strip() for h in headers]
    
    field_map = {
        "qTDetail": ["qtdetail", "question_title", "section", "group", "category", "title"],
        "uQDetail": ["uqdetail", "u_q_detail", "question", "question_detail", "detail"],
        "mQDetail": ["mqdetail", "m_q_detail", "question", "question_detail", "detail"],
        "qTID": ["qtid", "q_tid", "title_id", "titleid"],
        "yID": ["yid", "y_id", "year_id", "yearid"],
    }
    
    if org_type == "university":
        field_map["question_detail"] = ["uQDetail", "u_q_detail", "question", "question_detail"]
    else:
        field_map["question_detail"] = ["mQDetail", "m_q_detail", "question", "question_detail"]
    
    for target, possible_sources in field_map.items():
        for i, h in enumerate(headers_lower):
            if h in possible_sources:
                mapping[target] = headers[i]
                break
    
    return mapping


@router.post("/import/preview", response_model=ExcelImportPreview)
async def preview_excel_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Preview Excel import data before confirming."""
    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")
    
    headers, rows = parse_excel_file(content)
    if not headers:
        raise HTTPException(400, "No data found in file")
    
    org_type, year_id = detect_org_type_and_year(headers, rows)
    mapping = suggest_column_mapping(headers, org_type) if org_type else {}
    
    return ExcelImportPreview(
        headers=headers,
        rows=rows[:20],
        total_rows=len(rows),
        detected_org_type=org_type,
        detected_year_id=year_id,
        suggested_mapping=mapping,
    )


@router.post("/import/bulk", status_code=201)
def bulk_import_questions(
    data: BulkQuestionCreate,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Bulk create questions and titles from parsed Excel data into existing tables."""
    # Verify year exists in `year` table
    year = crud.get_year(db, data.year_id)
    if not year:
        raise HTTPException(404, "Year not found in `year` table")
    
    # Create question titles in `questiontitle` table
    title_mapping = crud.bulk_create_question_titles(db, data.question_titles)
    
    # Create questions in `uniquestion` or `ministryquestion` table
    if data.org_type == "university":
        created_ids = crud.bulk_create_uni_questions(db, data.questions, title_mapping)
    else:
        created_ids = crud.bulk_create_ministry_questions(db, data.questions, title_mapping)
    
    db.commit()
    
    return {
        "created_titles": len(title_mapping),
        "created_questions": len(created_ids),
        "question_ids": created_ids,
    }


# ============================================================
# Virtual Survey Forms (NO new table - defined by year + org_type)
# ============================================================

@router.get("/forms", response_model=list[SurveyFormVirtual])
def list_survey_forms(
    params: SurveyListParams = Depends(),
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """List virtual survey forms (year + org_type combinations that have questions)."""
    forms, total = crud.get_virtual_survey_forms(db, params)
    return forms


@router.get("/builder/{org_type}/{year_id}", response_model=SurveyFormWithQuestions)
def get_survey_builder(
    org_type: OrgType,
    year_id: int,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Get all data needed for the survey form builder (virtual form from year + org_type)."""
    data = crud.get_survey_builder_data(db, org_type, year_id)
    if not data:
        raise HTTPException(404, "Year not found or no questions for this combination")
    return data


@router.post("/builder/reorder")
def reorder_questions(
    data: ReorderQuestionsRequest,
    db: Session = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Reorder questions in a survey form (virtual - display_order for UI only)."""
    return {"message": "Order updated", "count": len(data.question_orders)}
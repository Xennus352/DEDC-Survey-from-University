"""Schemas for the admin survey form builder - using ONLY existing 10 tables."""
from datetime import date, datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


OrgType = Literal["university", "ministry"]
YearStatus = Literal[0, 1]  # 0=draft, 1=published
QuestionSourceType = Literal["questiontitle", "uniquestion", "ministryquestion"]


class YearInput(BaseModel):
    """Input for creating/updating a year period (uses `year` table)."""
    model_config = ConfigDict(extra="forbid")

    year_from: int = Field(ge=1, le=12, description="Month (1-12)")
    year_to: int = Field(ge=1900, le=2100, description="Year (e.g., 2024)")
    status: YearStatus = Field(default=0, description="0=draft, 1=published")

    @model_validator(mode="after")
    def validate_year(self):
        if self.year_from < 1 or self.year_from > 12:
            raise ValueError("year_from must be a valid month (1-12)")
        if self.year_to < 1900 or self.year_to > 2100:
            raise ValueError("year_to must be a valid year")
        return self


class YearOutput(BaseModel):
    """Output for a year period (from `year` table)."""
    model_config = ConfigDict(from_attributes=True)

    yID: int
    year_from: int
    year_to: int
    status: int
    label: str


class QuestionTitleInput(BaseModel):
    """Input for creating/updating a question title (uses `questiontitle` table)."""
    model_config = ConfigDict(extra="forbid")

    qTDetail: str = Field(min_length=1, max_length=10000, description="Question title text")
    description: Optional[str] = Field(default=None, max_length=10000, description="Optional description")


class QuestionTitleOutput(BaseModel):
    """Output for a question title (from `questiontitle` table)."""
    model_config = ConfigDict(from_attributes=True)

    qTID: int
    qTDetail: str
    description: Optional[str] = None


class UniQuestionInput(BaseModel):
    """Input for creating/updating a university question (uses `uniquestion` table)."""
    model_config = ConfigDict(extra="forbid")

    uQDetail: str = Field(min_length=1, max_length=10000, description="Question detail")
    qTID: Optional[int] = Field(default=None, description="Linked question title ID (questiontitle.qTID)")
    yID: int = Field(description="Year ID (year.yID) this question belongs to")


class UniQuestionOutput(BaseModel):
    """Output for a university question (from `uniquestion` table)."""
    model_config = ConfigDict(from_attributes=True)

    uQId: int
    uQDetail: str
    qTID: Optional[int] = None
    yID: int
    qTDetail: Optional[str] = None
    title_description: Optional[str] = None


class MinistryQuestionInput(BaseModel):
    """Input for creating/updating a ministry question (uses `ministryquestion` table)."""
    model_config = ConfigDict(extra="forbid")

    mQDetail: str = Field(min_length=1, max_length=10000, description="Question detail")
    qTID: Optional[int] = Field(default=None, description="Linked question title ID (questiontitle.qTID)")
    yID: int = Field(description="Year ID (year.yID) this question belongs to")


class MinistryQuestionOutput(BaseModel):
    """Output for a ministry question (from `ministryquestion` table)."""
    model_config = ConfigDict(from_attributes=True)

    mQId: int
    mQDetail: str
    qTID: Optional[int] = None
    yID: int
    qTDetail: Optional[str] = None
    title_description: Optional[str] = None


class SurveyFormVirtual(BaseModel):
    """Virtual survey form - defined by year + org_type combination (NO new table)."""
    model_config = ConfigDict(from_attributes=True)

    year_id: int
    year_label: str
    org_type: OrgType
    title: str
    description: Optional[str] = None
    is_active: bool
    question_count: int = 0


class SurveyQuestionLinkOutput(BaseModel):
    """Question link for form builder (virtual - no table)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    question_type: QuestionSourceType
    display_order: int
    is_required: bool
    question_detail: Optional[str] = None
    question_title: Optional[str] = None


class ExcelImportPreview(BaseModel):
    """Preview of Excel import data."""
    model_config = ConfigDict(extra="forbid")

    headers: list[str]
    rows: list[list[Any]]
    total_rows: int
    detected_org_type: Optional[OrgType] = None
    detected_year_id: Optional[int] = None
    suggested_mapping: dict[str, str] = Field(default_factory=dict)


class ExcelImportConfirm(BaseModel):
    """Confirmation for Excel import."""
    model_config = ConfigDict(extra="forbid")

    org_type: OrgType
    year_id: int
    mapping: dict[str, str] = Field(description="Column mapping: excel_col -> db_field")
    create_missing_questions: bool = Field(default=True)
    create_missing_titles: bool = Field(default=True)
    update_existing: bool = Field(default=False)


class BulkQuestionCreate(BaseModel):
    """Bulk create questions from import (uses existing tables only)."""
    model_config = ConfigDict(extra="forbid")

    org_type: OrgType
    year_id: int
    questions: list[dict[str, Any]] = Field(description="List of question data for uniquestion/ministryquestion")
    question_titles: list[dict[str, Any]] = Field(default_factory=list, description="List of question title data for questiontitle")


class SurveyFormWithQuestions(BaseModel):
    """Survey form with its questions for the builder (virtual form)."""
    model_config = ConfigDict(from_attributes=True)

    form: SurveyFormVirtual
    questions: list[SurveyQuestionLinkOutput]
    available_questions: list[UniQuestionOutput | MinistryQuestionOutput]
    available_titles: list[QuestionTitleOutput]
    years: list[YearOutput]
    organizations: list[dict[str, Any]]


class ReorderQuestionsRequest(BaseModel):
    """Request to reorder questions in a survey form (virtual - no table)."""
    model_config = ConfigDict(extra="forbid")

    question_orders: list[dict[str, int]] = Field(description="List of {question_id, display_order}")


class SurveyListParams(BaseModel):
    """Parameters for listing virtual survey forms (year + org_type combos)."""
    model_config = ConfigDict(extra="forbid")

    search: str = Field(default="", max_length=100)
    org_type: Optional[OrgType] = None
    year_id: Optional[int] = None
    is_active: Optional[bool] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=25, ge=1, le=100)


class YearListParams(BaseModel):
    """Parameters for listing years (from `year` table)."""
    model_config = ConfigDict(extra="forbid")

    search: str = Field(default="", max_length=100)
    status: Optional[YearStatus] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=100)


class QuestionListParams(BaseModel):
    """Parameters for listing questions (from `uniquestion`/`ministryquestion` tables)."""
    model_config = ConfigDict(extra="forbid")

    search: str = Field(default="", max_length=100)
    question_type: Optional[QuestionSourceType] = None
    year_id: Optional[int] = None
    title_id: Optional[int] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=100)

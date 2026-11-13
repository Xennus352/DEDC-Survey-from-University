"""Schemas for the admin survey form builder - using ONLY existing 10 tables."""
from datetime import date, datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class YearStatusUpdate(BaseModel):
    """Status-only update that must not rewrite the stored survey period."""

    model_config = ConfigDict(extra="forbid")

    status: YearStatus = Field(description="0=draft, 1=published")


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
    # New fields for legacy survey list
    year_status: int = 0  # 0=draft, 1=published
    year_from: Optional[int] = None  # Start year
    year_to: Optional[int] = None    # End year
    month_from: Optional[int] = None  # Start month
    month_to: Optional[int] = None    # End month
    question_title_count: int = 0    # Number of question titles


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


class QuestionUpdateItem(BaseModel):
    """One question row inside a group update.

    Items with an id rewrite that existing question; items without an id are
    inserted as new questions under the title.
    """

    model_config = ConfigDict(extra="forbid")

    id: Optional[int] = Field(
        default=None, ge=1, description="Question ID (uniquestion.uQId / ministryquestion.mQId); omit to insert a new question"
    )
    detail: str = Field(min_length=1, max_length=10000, description="Question text")

    @field_validator("detail")
    @classmethod
    def clean_detail(cls, value: str) -> str:
        detail = value.strip()
        if not detail:
            raise ValueError("Question text cannot be empty")
        return detail


class QuestionGroupUpdateInput(BaseModel):
    """Rename a question title and rewrite the questions under it for one year."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=10000, description="Updated question title text")
    questions: list[QuestionUpdateItem] = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Question title cannot be empty")
        return title

    @field_validator("questions")
    @classmethod
    def unique_question_ids(cls, value: list[QuestionUpdateItem]) -> list[QuestionUpdateItem]:
        ids = [item.id for item in value if item.id is not None]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate question ids are not allowed")
        return value


class QuestionGroupQuestionOutput(BaseModel):
    """One question under a title, for the edit modal."""

    id: int
    detail: str


class QuestionGroupOutput(BaseModel):
    """A question title with the questions under it for one year."""

    qTID: Optional[int] = None
    qTDetail: Optional[str] = None
    questions: list[QuestionGroupQuestionOutput]


class YearQuestionGroupsOutput(BaseModel):
    """All question groups (title + questions) of one year and audience."""

    year_id: int
    org_type: OrgType
    groups: list[QuestionGroupOutput]


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


class SurveyQuestionGroupInput(BaseModel):
    """One question title and the questions that belong to it."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=10000)
    description: Optional[str] = Field(default=None, max_length=10000)
    questions: list[str] = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Question title cannot be empty")
        return title

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        description = value.strip()
        return description or None

    @field_validator("questions")
    @classmethod
    def clean_questions(cls, values: list[str]) -> list[str]:
        questions = [value.strip() for value in values if value and value.strip()]
        if not questions:
            raise ValueError("At least one question is required")
        return questions


class LegacySurveyCreateInput(BaseModel):
    """Create a native DEDC survey (year range + question title groups + questions)."""

    model_config = ConfigDict(extra="forbid")

    org_type: OrgType
    start_year: int = Field(ge=1900, le=2100, description="Start year (e.g., 2024)")
    start_month: int = Field(ge=1, le=12, description="Start month (1-12)")
    end_year: int = Field(ge=1900, le=2100, description="End year (e.g., 2024)")
    end_month: int = Field(ge=1, le=12, description="End month (1-12)")
    status: YearStatus = 1
    groups: list[SurveyQuestionGroupInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_year_range(self):
        start = (self.start_year, self.start_month)
        end = (self.end_year, self.end_month)
        if start > end:
            raise ValueError("Start year/month must be before or equal to end year/month")
        return self


class CreatedSurveyQuestionGroup(BaseModel):
    """Result of inserting one question title group."""

    qTID: int
    qTDetail: str
    description: Optional[str] = None
    question_ids: list[int]


class CreatedSurveyFormOutput(BaseModel):
    """Result of inserting a complete native survey."""

    year_id: int
    org_type: OrgType
    groups: list[CreatedSurveyQuestionGroup]
    question_count: int

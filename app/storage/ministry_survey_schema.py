"""SQLAlchemy Core tables for the public ministry survey.

The ``year`` and ``questiontitle`` tables are shared with the university
survey schema so the live tables are described only once.
"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
)

from app.storage.university_survey_schema import metadata, questiontitle, year

ministry = Table(
    "ministry",
    metadata,
    Column("ministryId", Integer, primary_key=True, autoincrement=True),
    Column("ministryName", String(255), nullable=False, unique=True),
)

ministryquestion = Table(
    "ministryquestion",
    metadata,
    Column("mQId", Integer, primary_key=True, autoincrement=True),
    Column("mQDetail", Text, nullable=False),
    Column(
        "qTID",
        ForeignKey("questiontitle.qTID", ondelete="SET NULL", onupdate="CASCADE"),
    ),
    Column("yID", ForeignKey("year.yID"), nullable=False),
)

ministrysurvey = Table(
    "ministrysurvey",
    metadata,
    Column("mSurveyId", Integer, primary_key=True, autoincrement=True),
    Column(
        "ministryId",
        ForeignKey("ministry.ministryId", onupdate="CASCADE"),
        nullable=False,
    ),
    Column(
        "mQId",
        ForeignKey("ministryquestion.mQId", onupdate="CASCADE"),
        nullable=False,
    ),
    Column("hasItem", Boolean, nullable=False),
    Column("itemCount", Integer),
    Column("surveyDescription", Text),
    Column("remark", Text),
    Column(
        "submittedAt",
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    ),
    Column("updatedAt", DateTime),
)

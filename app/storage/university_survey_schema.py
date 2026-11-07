"""SQLAlchemy Core tables for the public university survey.

The live DEDC database extended the original eight-table model with ``year``,
``questiontitle`` and year/question links. These definitions mirror only the
tables the public university survey reads or writes. The ``year`` and
``questiontitle`` tables are shared with the ministry survey schema.
"""
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Table,
    Text,
    func,
)

metadata = MetaData()

year = Table(
    "year",
    metadata,
    Column("yID", Integer, primary_key=True, autoincrement=True),
    Column("yearFrom", Date),
    Column("yearTo", Date),
    Column("status", SmallInteger, server_default="1"),
)

questiontitle = Table(
    "questiontitle",
    metadata,
    Column("qTID", Integer, primary_key=True, autoincrement=True),
    Column("qTDetail", Text, nullable=False),
    Column("description", Text),
)

university = Table(
    "university",
    metadata,
    Column("uniId", Integer, primary_key=True, autoincrement=True),
    Column("uniType", String(100), nullable=False),
    Column("uniName", String(255), nullable=False, unique=True),
)

uniquestion = Table(
    "uniquestion",
    metadata,
    Column("uQId", Integer, primary_key=True, autoincrement=True),
    Column("uQDetail", Text, nullable=False),
    Column("qTID", ForeignKey("questiontitle.qTID", onupdate="CASCADE")),
    Column("yID", ForeignKey("year.yID", onupdate="CASCADE"), nullable=False),
)

unisurvey = Table(
    "unisurvey",
    metadata,
    Column("uniSurveyId", Integer, primary_key=True, autoincrement=True),
    Column(
        "uniId",
        ForeignKey("university.uniId", onupdate="CASCADE"),
        nullable=False,
    ),
    Column(
        "uQId",
        ForeignKey("uniquestion.uQId", onupdate="CASCADE"),
        nullable=False,
    ),
    Column("hasItem", Boolean, nullable=False),
    Column("itemCount", Integer),
    Column("surveyDescription", Text),
    Column("remark", Text),
    Column("submittedAt", DateTime, nullable=False, server_default=func.current_timestamp()),
    Column("updatedAt", DateTime),
)

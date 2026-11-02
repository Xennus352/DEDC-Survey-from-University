"""Mappings for existing university/ministry data; identifiers remain unchanged."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, func
from app.database import Base


class University(Base):
    __tablename__ = "university"
    id = Column("uniId", Integer, primary_key=True)
    kind = Column("uniType", String(100), nullable=False)
    name = Column("uniName", String(255), nullable=False)


class Ministry(Base):
    __tablename__ = "ministry"
    id = Column("ministryId", Integer, primary_key=True)
    name = Column("ministryName", String(255), nullable=False)


class ReportingYear(Base):
    __tablename__ = "year"
    id = Column("yID", Integer, primary_key=True)
    start = Column("yearFrom", Date)
    end = Column("yearTo", Date)


class QuestionTitle(Base):
    __tablename__ = "questiontitle"
    id = Column("qTID", Integer, primary_key=True)
    text = Column("qTDetail", Text, nullable=False)
    description = Column(Text)


class UniversityQuestion(Base):
    __tablename__ = "uniquestion"
    id = Column("uQId", Integer, primary_key=True)
    text = Column("uQDetail", Text, nullable=False)
    title_id = Column("qTID", Integer, ForeignKey("questiontitle.qTID"))
    year_id = Column("yID", Integer, ForeignKey("year.yID"), nullable=False)


class MinistryQuestion(Base):
    __tablename__ = "ministryquestion"
    id = Column("mQId", Integer, primary_key=True)
    text = Column("mQDetail", Text, nullable=False)
    title_id = Column("qTID", Integer, ForeignKey("questiontitle.qTID"))
    year_id = Column("yID", Integer, ForeignKey("year.yID"), nullable=False)


class UniversityAnswer(Base):
    __tablename__ = "unisurvey"
    id = Column("uniSurveyId", Integer, primary_key=True)
    organization_id = Column(
        "uniId", Integer, ForeignKey("university.uniId"), nullable=False
    )
    question_id = Column(
        "uQId", Integer, ForeignKey("uniquestion.uQId"), nullable=False
    )
    present = Column("hasItem", Integer, nullable=False)
    quantity = Column("itemCount", Integer)
    description = Column("surveyDescription", Text)
    remark = Column(Text)
    submitted_at = Column(
        "submittedAt", DateTime, nullable=False, server_default=func.now()
    )
    updated_at = Column("updatedAt", DateTime)


class MinistryAnswer(Base):
    __tablename__ = "ministrysurvey"
    id = Column("mSurveyId", Integer, primary_key=True)
    organization_id = Column(
        "ministryId", Integer, ForeignKey("ministry.ministryId"), nullable=False
    )
    question_id = Column(
        "mQId", Integer, ForeignKey("ministryquestion.mQId"), nullable=False
    )
    present = Column("hasItem", Integer, nullable=False)
    quantity = Column("itemCount", Integer)
    description = Column("surveyDescription", Text)
    remark = Column(Text)
    submitted_at = Column(
        "submittedAt", DateTime, nullable=False, server_default=func.now()
    )
    updated_at = Column("updatedAt", DateTime)

"""Models using ONLY the 10 existing tables from dedc.sql"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import declarative_base
Base = declarative_base()


# ============================================================
# EXISTING TABLES (from dedc.sql) - mapped with extend_existing
# ============================================================

class Ministry(Base):
    __tablename__ = "ministry"
    __table_args__ = {"extend_existing": True}
    ministryId = Column(Integer, primary_key=True)
    ministryName = Column(String(255), nullable=False, unique=True)


class University(Base):
    __tablename__ = "university"
    __table_args__ = {"extend_existing": True}
    uniId = Column(Integer, primary_key=True)
    uniType = Column(String(100), nullable=False)
    uniName = Column(String(255), nullable=False, unique=True)


class QuestionTitle(Base):
    __tablename__ = "questiontitle"
    __table_args__ = {"extend_existing": True}
    qTID = Column(Integer, primary_key=True)
    qTDetail = Column(Text, nullable=False)
    description = Column(Text)


class MinistryQuestion(Base):
    __tablename__ = "ministryquestion"
    __table_args__ = {"extend_existing": True}
    mQId = Column(Integer, primary_key=True)
    mQDetail = Column(Text, nullable=False)
    qTID = Column(Integer, ForeignKey("questiontitle.qTID"), nullable=True, index=True)
    yID = Column(Integer, ForeignKey("year.yID"), nullable=False, index=True)


class UniQuestion(Base):
    __tablename__ = "uniquestion"
    __table_args__ = {"extend_existing": True}
    uQId = Column(Integer, primary_key=True)
    uQDetail = Column(Text, nullable=False)
    qTID = Column(Integer, ForeignKey("questiontitle.qTID"), nullable=True, index=True)
    yID = Column(Integer, ForeignKey("year.yID"), nullable=False, index=True)


class Year(Base):
    __tablename__ = "year"
    __table_args__ = {"extend_existing": True}
    yID = Column(Integer, primary_key=True)
    yearFrom = Column(Date, nullable=True)  # month (1-12)
    yearTo = Column(Date, nullable=True)    # year (e.g., 2024)
    status = Column(Integer, nullable=False, default=0)  # 0=draft, 1=published


class MinistrySurvey(Base):
    __tablename__ = "ministrysurvey"
    __table_args__ = {"extend_existing": True}
    mSurveyId = Column(Integer, primary_key=True)
    ministryId = Column(Integer, ForeignKey("ministry.ministryId"), nullable=False, index=True)
    mQId = Column(Integer, ForeignKey("ministryquestion.mQId"), nullable=False, index=True)
    hasItem = Column(Boolean, nullable=False)
    itemCount = Column(Integer, nullable=True)
    surveyDescription = Column(Text, nullable=True)
    remark = Column(Text, nullable=True)
    submittedAt = Column(DateTime, nullable=False, server_default=func.now())
    updatedAt = Column(DateTime, nullable=True, onupdate=func.now())


class UniSurvey(Base):
    __tablename__ = "unisurvey"
    __table_args__ = {"extend_existing": True}
    uniSurveyId = Column(Integer, primary_key=True)
    uniId = Column(Integer, ForeignKey("university.uniId"), nullable=False, index=True)
    uQId = Column(Integer, ForeignKey("uniquestion.uQId"), nullable=False, index=True)
    hasItem = Column(Boolean, nullable=False)
    itemCount = Column(Integer, nullable=True)
    surveyDescription = Column(Text, nullable=True)
    remark = Column(Text, nullable=True)
    submittedAt = Column(DateTime, nullable=False, server_default=func.now())
    updatedAt = Column(DateTime, nullable=True, onupdate=func.now())


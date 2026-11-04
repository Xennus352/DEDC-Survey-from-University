"""Memory-only projections of source definitions preserved in JSON metadata."""

from sqlalchemy import Column, Date, ForeignKey, Integer, Text
from app.database import Base


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

from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("surveys.id"))
    respondent_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    survey = relationship("Survey", back_populates="responses")
    answers = relationship("Answer", back_populates="response")

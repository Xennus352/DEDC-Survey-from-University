from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AnswerBase(BaseModel):
    question_id: int
    answer_text: Optional[str] = None
    option_id: Optional[int] = None


class AnswerCreate(AnswerBase):
    pass


class Answer(AnswerBase):
    id: int

    class Config:
        from_attributes = True


class ResponseBase(BaseModel):
    survey_id: int
    respondent_id: Optional[str] = None


class ResponseCreate(ResponseBase):
    answers: List[AnswerCreate]


class Response(ResponseBase):
    id: int
    created_at: datetime
    answers: List[Answer] = []

    class Config:
        from_attributes = True

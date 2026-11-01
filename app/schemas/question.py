from typing import List, Optional

from pydantic import BaseModel


class OptionBase(BaseModel):
    text: str


class OptionCreate(OptionBase):
    pass


class Option(OptionBase):
    id: int

    class Config:
        from_attributes = True


class QuestionBase(BaseModel):
    text: str
    question_type: str


class QuestionCreate(QuestionBase):
    options: Optional[List[OptionCreate]] = []


class Question(QuestionBase):
    id: int
    survey_id: int
    options: List[Option] = []

    class Config:
        from_attributes = True

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class SurveyBase(BaseModel):
    title: str
    year: int


class SurveyCreate(SurveyBase):
    pass


class Survey(SurveyBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

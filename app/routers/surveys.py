from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.dependencies import get_db
from app.schemas import survey as survey_schema

router = APIRouter(prefix="/surveys", tags=["surveys"])


@router.post("/", response_model=survey_schema.Survey)
def create_survey(survey: survey_schema.SurveyCreate, db: Session = Depends(get_db)):
    return crud.survey.create_survey(db=db, survey_data=survey)


@router.get("/", response_model=List[survey_schema.Survey])
def read_surveys(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    surveys = crud.survey.get_surveys(db, skip=skip, limit=limit)
    return surveys


@router.get("/year/{year}", response_model=List[survey_schema.Survey])
def read_surveys_by_year(year: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    surveys = crud.survey.get_surveys_by_year(db, year=year, skip=skip, limit=limit)
    return surveys


@router.get("/{survey_id}", response_model=survey_schema.Survey)
def read_survey(survey_id: int, db: Session = Depends(get_db)):
    db_survey = crud.survey.get_survey(db, survey_id=survey_id)
    if db_survey is None:
        raise HTTPException(status_code=404, detail="Survey not found")
    return db_survey


@router.delete("/{survey_id}", response_model=survey_schema.Survey)
def delete_survey(survey_id: int, db: Session = Depends(get_db)):
    db_survey = crud.survey.delete_survey(db, survey_id=survey_id)
    if db_survey is None:
        raise HTTPException(status_code=404, detail="Survey not found")
    return db_survey

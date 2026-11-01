from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models
from app.dependencies import get_db
from app.schemas import response as response_schema

router = APIRouter(prefix="/responses", tags=["responses"])


@router.post("/", response_model=response_schema.Response)
def create_response(response: response_schema.ResponseCreate, db: Session = Depends(get_db)):
    db_survey = db.query(models.Survey).filter(models.Survey.id == response.survey_id).first()
    if not db_survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return crud.response.create_response(db=db, response_data=response)


@router.get("/{response_id}", response_model=response_schema.Response)
def read_response(response_id: int, db: Session = Depends(get_db)):
    db_response = crud.response.get_response(db, response_id=response_id)
    if db_response is None:
        raise HTTPException(status_code=404, detail="Response not found")
    return db_response


@router.get("/survey/{survey_id}", response_model=List[response_schema.Response])
def read_responses_by_survey(survey_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    responses = crud.response.get_responses_by_survey(db, survey_id=survey_id, skip=skip, limit=limit)
    return responses

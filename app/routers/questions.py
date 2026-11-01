from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.dependencies import get_db
from app.schemas import question as question_schema

router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("/survey/{survey_id}", response_model=question_schema.Question)
def create_question(survey_id: int, question: question_schema.QuestionCreate, db: Session = Depends(get_db)):
    db_survey = db.query(models.Survey).filter(models.Survey.id == survey_id).first()
    if not db_survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    db_question = models.Question(
        survey_id=survey_id, text=question.text, question_type=question.question_type
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)

    for opt in question.options:
        db_option = models.Option(question_id=db_question.id, text=opt.text)
        db.add(db_option)
    db.commit()
    db.refresh(db_question)
    return db_question


@router.get("/survey/{survey_id}", response_model=List[question_schema.Question])
def read_questions_by_survey(survey_id: int, db: Session = Depends(get_db)):
    questions = db.query(models.Question).filter(models.Question.survey_id == survey_id).all()
    return questions

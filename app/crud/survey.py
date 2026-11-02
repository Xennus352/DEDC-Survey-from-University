from sqlalchemy.orm import Session

from app.models import survey


def get_survey(db: Session, survey_id: int):
    return db.query(survey.Survey).filter(survey.Survey.id == survey_id).first()


def get_surveys(db: Session, skip: int = 0, limit: int = 100):
    return db.query(survey.Survey).offset(skip).limit(limit).all()


def get_surveys_by_year(db: Session, year: int, skip: int = 0, limit: int = 100):
    return db.query(survey.Survey).filter(survey.Survey.year == year).offset(skip).limit(limit).all()


def create_survey(db: Session, survey_data):
    db_survey = survey.Survey(**survey_data.model_dump())
    db.add(db_survey)
    db.commit()
    db.refresh(db_survey)
    return db_survey


def delete_survey(db: Session, survey_id: int):
    db_survey = get_survey(db, survey_id)
    if db_survey:
        db.delete(db_survey)
        db.commit()
    return db_survey

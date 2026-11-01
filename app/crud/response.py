from sqlalchemy.orm import Session

from app.models import response, answer


def create_response(db: Session, response_data):
    db_response = response.Response(
        survey_id=response_data.survey_id, respondent_id=response_data.respondent_id
    )
    db.add(db_response)
    db.commit()
    db.refresh(db_response)

    for ans in response_data.answers:
        db_answer = answer.Answer(
            response_id=db_response.id,
            question_id=ans.question_id,
            answer_text=ans.answer_text,
            option_id=ans.option_id,
        )
        db.add(db_answer)

    db.commit()
    db.refresh(db_response)
    return db_response


def get_response(db: Session, response_id: int):
    return db.query(response.Response).filter(response.Response.id == response_id).first()


def get_responses_by_survey(db: Session, survey_id: int, skip: int = 0, limit: int = 100):
    return (
        db.query(response.Response)
        .filter(response.Response.survey_id == survey_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

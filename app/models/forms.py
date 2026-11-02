"""Normalized, version-specific definitions alongside the existing survey tables."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship
from app.database import Base


class SurveyForm(Base):
    __tablename__ = "survey_forms"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    audience = Column(String(20), nullable=False, default="university")
    archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    versions = relationship(
        "FormVersion",
        back_populates="form",
        order_by="FormVersion.number",
        cascade="all, delete-orphan",
    )


class FormVersion(Base):
    __tablename__ = "survey_form_versions"
    __table_args__ = (UniqueConstraint("form_id", "number"),)
    id = Column(Integer, primary_key=True)
    form_id = Column(Integer, ForeignKey("survey_forms.id"), nullable=False, index=True)
    number = Column(Integer, nullable=False, default=1)
    revision = Column(Integer, nullable=False, default=1)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    language = Column(String(10), nullable=False, default="my")
    status = Column(String(20), nullable=False, default="draft", index=True)
    starts_at = Column(DateTime)
    ends_at = Column(DateTime)
    published_at = Column(DateTime)
    reporting_start = Column(Date)
    reporting_end = Column(Date)
    form = relationship("SurveyForm", back_populates="versions")
    sections = relationship(
        "FormSection",
        back_populates="version",
        order_by="FormSection.position",
        cascade="all, delete-orphan",
    )


class FormSection(Base):
    __tablename__ = "survey_sections"
    id = Column(Integer, primary_key=True)
    version_id = Column(
        Integer, ForeignKey("survey_form_versions.id"), nullable=False, index=True
    )
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False, default="")
    position = Column(Integer, nullable=False, default=0)
    enabled = Column(Boolean, nullable=False, default=True)
    conditions = Column(JSON)
    source_title_id = Column(Integer, ForeignKey("questiontitle.qTID"))
    version = relationship("FormVersion", back_populates="sections")
    questions = relationship(
        "FormField",
        back_populates="section",
        order_by="FormField.position",
        cascade="all, delete-orphan",
    )


class FormField(Base):
    __tablename__ = "survey_fields"
    __table_args__ = (UniqueConstraint("version_id", "key"),)
    id = Column(Integer, primary_key=True)
    version_id = Column(
        Integer, ForeignKey("survey_form_versions.id"), nullable=False, index=True
    )
    section_id = Column(
        Integer, ForeignKey("survey_sections.id"), nullable=False, index=True
    )
    key = Column(String(100), nullable=False)
    title = Column(Text, nullable=False)
    title_my = Column(Text, nullable=False, default="")
    title_en = Column(Text, nullable=False, default="")
    kind = Column(String(40), nullable=False)
    help_text = Column(Text, nullable=False, default="")
    placeholder = Column(String(255), nullable=False, default="")
    required = Column(Boolean, nullable=False, default=False)
    enabled = Column(Boolean, nullable=False, default=True)
    position = Column(Integer, nullable=False, default=0)
    config = Column(JSON, nullable=False, default=dict)
    conditions = Column(JSON)
    source_university_question_id = Column(Integer, ForeignKey("uniquestion.uQId"))
    source_ministry_question_id = Column(Integer, ForeignKey("ministryquestion.mQId"))
    section = relationship("FormSection", back_populates="questions")
    options = relationship(
        "FieldOption", order_by="FieldOption.position", cascade="all, delete-orphan"
    )


class FieldOption(Base):
    __tablename__ = "survey_field_options"
    __table_args__ = (UniqueConstraint("field_id", "value"),)
    id = Column(Integer, primary_key=True)
    field_id = Column(
        Integer, ForeignKey("survey_fields.id"), nullable=False, index=True
    )
    value = Column(String(255), nullable=False)
    label = Column(String(1024), nullable=False)
    position = Column(Integer, nullable=False, default=0)


class Submission(Base):
    __tablename__ = "survey_submissions"
    id = Column(Integer, primary_key=True)
    version_id = Column(
        Integer, ForeignKey("survey_form_versions.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("user.userId"), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="completed", index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    reporting_start = Column(Date)
    reporting_end = Column(Date)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    location = Column(JSON, nullable=False, default=dict)
    answers = relationship("FieldAnswer", cascade="all, delete-orphan")
    version = relationship("FormVersion")


class FieldAnswer(Base):
    __tablename__ = "survey_field_answers"
    __table_args__ = (UniqueConstraint("submission_id", "field_id"),)
    id = Column(Integer, primary_key=True)
    submission_id = Column(
        Integer, ForeignKey("survey_submissions.id"), nullable=False, index=True
    )
    field_id = Column(Integer, ForeignKey("survey_fields.id"), nullable=False)
    value = Column(JSON)


class WorkbookImport(Base):
    __tablename__ = "survey_workbook_imports"
    __table_args__ = (UniqueConstraint("digest", "worksheet"),)
    id = Column(Integer, primary_key=True)
    digest = Column(String(64), nullable=False)
    worksheet = Column(String(255), nullable=False)
    version_id = Column(Integer, ForeignKey("survey_form_versions.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("user.userId"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    rows = relationship("WorkbookAnswer", cascade="all, delete-orphan")


class WorkbookAnswer(Base):
    """Immutable source observations; never mistaken for defaults or submissions."""

    __tablename__ = "survey_workbook_answers"
    id = Column(Integer, primary_key=True)
    import_id = Column(
        Integer, ForeignKey("survey_workbook_imports.id"), nullable=False, index=True
    )
    number = Column(String(50), nullable=False)
    question = Column(Text, nullable=False)
    source_cell = Column(String(30), nullable=False)
    present_text = Column(Text, nullable=False, default="")
    absent_text = Column(Text, nullable=False, default="")
    quantity_text = Column(Text, nullable=False, default="")
    details_text = Column(Text, nullable=False, default="")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey("user.userId"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity = Column(String(100), nullable=False)
    target_id = Column(Integer)
    changes = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)


from sqlalchemy import LargeBinary
from sqlalchemy.dialects.mysql import LONGBLOB


class AnswerFile(Base):
    __tablename__ = "survey_answer_files"
    id = Column(Integer, primary_key=True)
    version_id = Column(
        Integer, ForeignKey("survey_form_versions.id"), nullable=False, index=True
    )
    field_id = Column(
        Integer, ForeignKey("survey_fields.id", ondelete="SET NULL"), nullable=True
    )
    field_key = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("user.userId"), nullable=False, index=True)
    submission_id = Column(Integer, ForeignKey("survey_submissions.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    media_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False)
    content = Column(LargeBinary().with_variant(LONGBLOB(), "mysql"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class WorkbookTemplate(Base):
    __tablename__ = "survey_workbook_templates"
    digest = Column(String(64), primary_key=True)
    filename = Column(String(255), nullable=False)
    content = Column(LargeBinary().with_variant(LONGBLOB(), "mysql"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

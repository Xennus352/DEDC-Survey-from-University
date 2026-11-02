"""Add versioned definitions, source workbook observations, submissions and audit logs."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("survey_forms"):
        op.create_table(
            "survey_forms",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("audience", sa.String(length=20), nullable=False),
            sa.Column("archived", sa.Boolean(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if not sa.inspect(bind).has_table("survey_form_versions"):
        op.create_table(
            "survey_form_versions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("form_id", sa.Integer(), nullable=False),
            sa.Column("number", sa.Integer(), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("language", sa.String(length=10), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("starts_at", sa.DateTime(), nullable=True),
            sa.Column("ends_at", sa.DateTime(), nullable=True),
            sa.Column("published_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["form_id"],
                ["survey_forms.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("form_id", "number"),
        )
        op.create_index(
            op.f("ix_survey_form_versions_status"),
            "survey_form_versions",
            ["status"],
            unique=False,
        )
        op.create_index(
            op.f("ix_survey_form_versions_form_id"),
            "survey_form_versions",
            ["form_id"],
            unique=False,
        )
    if not sa.inspect(bind).has_table("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("actor_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=100), nullable=False),
            sa.Column("entity", sa.String(length=100), nullable=False),
            sa.Column("target_id", sa.Integer(), nullable=True),
            sa.Column("changes", sa.JSON(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["actor_id"],
                ["user.userId"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False
        )
        op.create_index(
            op.f("ix_audit_logs_actor_id"), "audit_logs", ["actor_id"], unique=False
        )
        op.create_index(
            op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False
        )
    if not sa.inspect(bind).has_table("survey_sections"):
        op.create_table(
            "survey_sections",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("version_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("conditions", sa.JSON(), nullable=True),
            sa.Column("source_title_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["source_title_id"],
                ["questiontitle.qTID"],
            ),
            sa.ForeignKeyConstraint(
                ["version_id"],
                ["survey_form_versions.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_survey_sections_version_id"),
            "survey_sections",
            ["version_id"],
            unique=False,
        )
    if not sa.inspect(bind).has_table("survey_submissions"):
        op.create_table(
            "survey_submissions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("version_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("location", sa.JSON(), nullable=False),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["user.userId"],
            ),
            sa.ForeignKeyConstraint(
                ["version_id"],
                ["survey_form_versions.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_survey_submissions_version_id"),
            "survey_submissions",
            ["version_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_survey_submissions_user_id"),
            "survey_submissions",
            ["user_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_survey_submissions_created_at"),
            "survey_submissions",
            ["created_at"],
            unique=False,
        )
        op.create_index(
            op.f("ix_survey_submissions_status"),
            "survey_submissions",
            ["status"],
            unique=False,
        )
    if not sa.inspect(bind).has_table("survey_workbook_imports"):
        op.create_table(
            "survey_workbook_imports",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("digest", sa.String(length=64), nullable=False),
            sa.Column("worksheet", sa.String(length=255), nullable=False),
            sa.Column("version_id", sa.Integer(), nullable=False),
            sa.Column("actor_id", sa.Integer(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["actor_id"],
                ["user.userId"],
            ),
            sa.ForeignKeyConstraint(
                ["version_id"],
                ["survey_form_versions.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("digest", "worksheet"),
        )
    if not sa.inspect(bind).has_table("survey_fields"):
        op.create_table(
            "survey_fields",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("version_id", sa.Integer(), nullable=False),
            sa.Column("section_id", sa.Integer(), nullable=False),
            sa.Column("key", sa.String(length=100), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("title_my", sa.Text(), nullable=False),
            sa.Column("title_en", sa.Text(), nullable=False),
            sa.Column("kind", sa.String(length=40), nullable=False),
            sa.Column("help_text", sa.Text(), nullable=False),
            sa.Column("placeholder", sa.String(length=255), nullable=False),
            sa.Column("required", sa.Boolean(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("config", sa.JSON(), nullable=False),
            sa.Column("conditions", sa.JSON(), nullable=True),
            sa.Column("source_university_question_id", sa.Integer(), nullable=True),
            sa.Column("source_ministry_question_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["section_id"],
                ["survey_sections.id"],
            ),
            sa.ForeignKeyConstraint(
                ["source_ministry_question_id"],
                ["ministryquestion.mQId"],
            ),
            sa.ForeignKeyConstraint(
                ["source_university_question_id"],
                ["uniquestion.uQId"],
            ),
            sa.ForeignKeyConstraint(
                ["version_id"],
                ["survey_form_versions.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("version_id", "key"),
        )
        op.create_index(
            op.f("ix_survey_fields_version_id"),
            "survey_fields",
            ["version_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_survey_fields_section_id"),
            "survey_fields",
            ["section_id"],
            unique=False,
        )
    if not sa.inspect(bind).has_table("survey_workbook_answers"):
        op.create_table(
            "survey_workbook_answers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("import_id", sa.Integer(), nullable=False),
            sa.Column("number", sa.String(length=50), nullable=False),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("source_cell", sa.String(length=30), nullable=False),
            sa.Column("present_text", sa.Text(), nullable=False),
            sa.Column("absent_text", sa.Text(), nullable=False),
            sa.Column("quantity_text", sa.Text(), nullable=False),
            sa.Column("details_text", sa.Text(), nullable=False),
            sa.ForeignKeyConstraint(
                ["import_id"],
                ["survey_workbook_imports.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_survey_workbook_answers_import_id"),
            "survey_workbook_answers",
            ["import_id"],
            unique=False,
        )
    if not sa.inspect(bind).has_table("survey_field_answers"):
        op.create_table(
            "survey_field_answers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("submission_id", sa.Integer(), nullable=False),
            sa.Column("field_id", sa.Integer(), nullable=False),
            sa.Column("value", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(
                ["field_id"],
                ["survey_fields.id"],
            ),
            sa.ForeignKeyConstraint(
                ["submission_id"],
                ["survey_submissions.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("submission_id", "field_id"),
        )
        op.create_index(
            op.f("ix_survey_field_answers_submission_id"),
            "survey_field_answers",
            ["submission_id"],
            unique=False,
        )
    if not sa.inspect(bind).has_table("survey_field_options"):
        op.create_table(
            "survey_field_options",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("field_id", sa.Integer(), nullable=False),
            sa.Column("value", sa.String(length=255), nullable=False),
            sa.Column("label", sa.String(length=1024), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["field_id"],
                ["survey_fields.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("field_id", "value"),
        )
        op.create_index(
            op.f("ix_survey_field_options_field_id"),
            "survey_field_options",
            ["field_id"],
            unique=False,
        )


def downgrade():
    raise RuntimeError(
        "Destructive downgrade is disabled; use a reviewed backup/restore procedure."
    )

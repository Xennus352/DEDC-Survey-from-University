"""Preserve existing tables and establish the legacy API baseline."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("admin_sessions"):
        op.create_table(
            "admin_sessions",
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("expires_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("token_hash"),
        )
        op.create_index(
            op.f("ix_admin_sessions_expires_at"),
            "admin_sessions",
            ["expires_at"],
            unique=False,
        )
    if not sa.inspect(bind).has_table("ministry"):
        op.create_table(
            "ministry",
            sa.Column("ministryId", sa.Integer(), nullable=False),
            sa.Column("ministryName", sa.String(length=255), nullable=False),
            sa.PrimaryKeyConstraint("ministryId"),
        )
    if not sa.inspect(bind).has_table("questiontitle"):
        op.create_table(
            "questiontitle",
            sa.Column("qTID", sa.Integer(), nullable=False),
            sa.Column("qTDetail", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("qTID"),
        )
    if not sa.inspect(bind).has_table("surveys"):
        op.create_table(
            "surveys",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("year", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_surveys_id"), "surveys", ["id"], unique=False)
        op.create_index(op.f("ix_surveys_year"), "surveys", ["year"], unique=False)
        op.create_index(op.f("ix_surveys_title"), "surveys", ["title"], unique=False)
    if not sa.inspect(bind).has_table("university"):
        op.create_table(
            "university",
            sa.Column("uniId", sa.Integer(), nullable=False),
            sa.Column("uniType", sa.String(length=100), nullable=False),
            sa.Column("uniName", sa.String(length=255), nullable=False),
            sa.PrimaryKeyConstraint("uniId"),
        )
    if not sa.inspect(bind).has_table("userrole"):
        op.create_table(
            "userrole",
            sa.Column("roleId", sa.Integer(), nullable=False),
            sa.Column("roleName", sa.String(length=100), nullable=False),
            sa.PrimaryKeyConstraint("roleId"),
        )
    if not sa.inspect(bind).has_table("year"):
        op.create_table(
            "year",
            sa.Column("yID", sa.Integer(), nullable=False),
            sa.Column("yearFrom", sa.Date(), nullable=True),
            sa.Column("yearTo", sa.Date(), nullable=True),
            sa.PrimaryKeyConstraint("yID"),
        )
    if not sa.inspect(bind).has_table("ministryquestion"):
        op.create_table(
            "ministryquestion",
            sa.Column("mQId", sa.Integer(), nullable=False),
            sa.Column("mQDetail", sa.Text(), nullable=False),
            sa.Column("qTID", sa.Integer(), nullable=True),
            sa.Column("yID", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["qTID"],
                ["questiontitle.qTID"],
            ),
            sa.ForeignKeyConstraint(
                ["yID"],
                ["year.yID"],
            ),
            sa.PrimaryKeyConstraint("mQId"),
        )
    if not sa.inspect(bind).has_table("questions"):
        op.create_table(
            "questions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("survey_id", sa.Integer(), nullable=True),
            sa.Column("text", sa.String(length=4096), nullable=True),
            sa.Column("question_type", sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(
                ["survey_id"],
                ["surveys.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_questions_id"), "questions", ["id"], unique=False)
    if not sa.inspect(bind).has_table("responses"):
        op.create_table(
            "responses",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("survey_id", sa.Integer(), nullable=True),
            sa.Column("respondent_id", sa.String(length=255), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(
                ["survey_id"],
                ["surveys.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_responses_id"), "responses", ["id"], unique=False)
    if not sa.inspect(bind).has_table("uniquestion"):
        op.create_table(
            "uniquestion",
            sa.Column("uQId", sa.Integer(), nullable=False),
            sa.Column("uQDetail", sa.Text(), nullable=False),
            sa.Column("qTID", sa.Integer(), nullable=True),
            sa.Column("yID", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["qTID"],
                ["questiontitle.qTID"],
            ),
            sa.ForeignKeyConstraint(
                ["yID"],
                ["year.yID"],
            ),
            sa.PrimaryKeyConstraint("uQId"),
        )
    if not sa.inspect(bind).has_table("user"):
        op.create_table(
            "user",
            sa.Column("userId", sa.Integer(), nullable=False),
            sa.Column("roleId", sa.Integer(), nullable=False),
            sa.Column("uniId", sa.Integer(), nullable=True),
            sa.Column("ministryId", sa.Integer(), nullable=True),
            sa.Column("userName", sa.String(length=100), nullable=False),
            sa.Column("passwordHash", sa.String(length=255), nullable=False),
            sa.Column("isActive", sa.Boolean(), nullable=False),
            sa.Column(
                "createdAt",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["roleId"],
                ["userrole.roleId"],
            ),
            sa.PrimaryKeyConstraint("userId"),
        )
    if not sa.inspect(bind).has_table("ministrysurvey"):
        op.create_table(
            "ministrysurvey",
            sa.Column("mSurveyId", sa.Integer(), nullable=False),
            sa.Column("ministryId", sa.Integer(), nullable=False),
            sa.Column("mQId", sa.Integer(), nullable=False),
            sa.Column("hasItem", sa.Integer(), nullable=False),
            sa.Column("itemCount", sa.Integer(), nullable=True),
            sa.Column("surveyDescription", sa.Text(), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column(
                "submittedAt",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("updatedAt", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["mQId"],
                ["ministryquestion.mQId"],
            ),
            sa.ForeignKeyConstraint(
                ["ministryId"],
                ["ministry.ministryId"],
            ),
            sa.PrimaryKeyConstraint("mSurveyId"),
        )
    if not sa.inspect(bind).has_table("options"):
        op.create_table(
            "options",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("question_id", sa.Integer(), nullable=True),
            sa.Column("text", sa.String(length=1024), nullable=True),
            sa.ForeignKeyConstraint(
                ["question_id"],
                ["questions.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_options_id"), "options", ["id"], unique=False)
    if not sa.inspect(bind).has_table("unisurvey"):
        op.create_table(
            "unisurvey",
            sa.Column("uniSurveyId", sa.Integer(), nullable=False),
            sa.Column("uniId", sa.Integer(), nullable=False),
            sa.Column("uQId", sa.Integer(), nullable=False),
            sa.Column("hasItem", sa.Integer(), nullable=False),
            sa.Column("itemCount", sa.Integer(), nullable=True),
            sa.Column("surveyDescription", sa.Text(), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column(
                "submittedAt",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("updatedAt", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["uQId"],
                ["uniquestion.uQId"],
            ),
            sa.ForeignKeyConstraint(
                ["uniId"],
                ["university.uniId"],
            ),
            sa.PrimaryKeyConstraint("uniSurveyId"),
        )
    if not sa.inspect(bind).has_table("answers"):
        op.create_table(
            "answers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("response_id", sa.Integer(), nullable=True),
            sa.Column("question_id", sa.Integer(), nullable=True),
            sa.Column("answer_text", sa.String(length=4096), nullable=True),
            sa.Column("option_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["option_id"],
                ["options.id"],
            ),
            sa.ForeignKeyConstraint(
                ["question_id"],
                ["questions.id"],
            ),
            sa.ForeignKeyConstraint(
                ["response_id"],
                ["responses.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_answers_id"), "answers", ["id"], unique=False)


def downgrade():
    raise RuntimeError(
        "Destructive downgrade is disabled; use a reviewed backup/restore procedure."
    )

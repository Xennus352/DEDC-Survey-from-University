"""Add authorized answer attachments without modifying stored records."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("survey_answer_files"):
        op.create_table(
            "survey_answer_files",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("version_id", sa.Integer(), nullable=False),
            sa.Column("field_id", sa.Integer(), nullable=True),
            sa.Column("field_key", sa.String(length=100), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("submission_id", sa.Integer(), nullable=True),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("media_type", sa.String(length=100), nullable=False),
            sa.Column("size", sa.Integer(), nullable=False),
            sa.Column(
                "content",
                sa.LargeBinary().with_variant(mysql.LONGBLOB(), "mysql"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["field_id"], ["survey_fields.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["submission_id"],
                ["survey_submissions.id"],
            ),
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
            op.f("ix_survey_answer_files_version_id"),
            "survey_answer_files",
            ["version_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_survey_answer_files_user_id"),
            "survey_answer_files",
            ["user_id"],
            unique=False,
        )


def downgrade():
    raise RuntimeError("Destructive downgrade is disabled.")

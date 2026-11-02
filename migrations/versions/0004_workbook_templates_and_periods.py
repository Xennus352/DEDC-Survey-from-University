"""Archive original workbook formatting and record reporting periods additively."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("survey_workbook_templates"):
        op.create_table(
            "survey_workbook_templates",
            sa.Column("digest", sa.String(64), primary_key=True),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column(
                "content",
                sa.LargeBinary().with_variant(mysql.LONGBLOB(), "mysql"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
    for table in ["survey_form_versions", "survey_submissions"]:
        existing = {column["name"] for column in sa.inspect(bind).get_columns(table)}
        for name in ["reporting_start", "reporting_end"]:
            if name not in existing:
                op.add_column(table, sa.Column(name, sa.Date(), nullable=True))


def downgrade():
    raise RuntimeError(
        "Destructive downgrade is disabled; historical periods and templates are retained."
    )

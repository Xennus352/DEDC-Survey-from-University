"""Add question bank table for reusable questions."""
from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "question_bank_questions" not in existing_tables:
        op.create_table(
            "question_bank_questions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("title_my", sa.Text(), nullable=False, default=""),
            sa.Column("title_en", sa.Text(), nullable=False, default=""),
            sa.Column("kind", sa.String(length=40), nullable=False, default="short_text"),
            sa.Column("help_text", sa.Text(), nullable=False, default=""),
            sa.Column("placeholder", sa.String(length=255), nullable=False, default=""),
            sa.Column("required", sa.Boolean(), nullable=False, default=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, default=True),
            sa.Column("config", sa.JSON(), nullable=False, default=dict),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint(
                "title", "kind", name="uq_question_bank_title_kind"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_question_bank_questions_title"),
            "question_bank_questions",
            ["title"],
            unique=False,
        )
        op.create_index(
            op.f("ix_question_bank_questions_kind"),
            "question_bank_questions",
            ["kind"],
            unique=False,
        )
        op.create_index(
            op.f("ix_question_bank_questions_enabled"),
            "question_bank_questions",
            ["enabled"],
            unique=False,
        )
        op.create_index(
            op.f("ix_question_bank_questions_created_at"),
            "question_bank_questions",
            ["created_at"],
            unique=False,
        )


def downgrade():
    op.drop_table("question_bank_questions")
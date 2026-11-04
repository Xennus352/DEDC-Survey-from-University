"""Retire the empty original API and organization tables, preserving dynamic forms.

Stop application writes before applying this migration. Preflight every table
before DDL because MySQL schema changes are not transactionally reversible.
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

# Children precede their parents. uniquestion, questiontitle and year are retained.
RETIRED = (
    "answers", "options", "responses", "questions", "surveys",
    "unisurvey", "ministrysurvey", "ministryquestion", "university", "ministry",
)
ALLOWED_REFERENCES = {
    ("user", "uniId"),
    ("user", "ministryId"),
    ("survey_fields", "source_ministry_question_id"),
}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())
    quote = bind.dialect.identifier_preparer.quote
    # Refuse to silently discard any records, even on a different deployment.
    for name in RETIRED:
        if name in existing and bind.execute(
            sa.text(f"SELECT COUNT(*) FROM {quote(name)}")
        ).scalar():
            raise RuntimeError(f"Cannot retire nonempty table {name}; migrate its records first.")

    references = {}
    for name in sorted(existing - set(RETIRED)):
        for fk in inspector.get_foreign_keys(name):
            if fk["referred_table"] not in RETIRED:
                continue
            columns = fk["constrained_columns"]
            if len(columns) != 1 or (name, columns[0]) not in ALLOWED_REFERENCES:
                raise RuntimeError(f"Unexpected reference from {name} to {fk['referred_table']}.")
            references.setdefault(name, []).append(fk)
    # Also check deployments whose membership/provenance columns have no FK.
    for name, column in ALLOWED_REFERENCES:
        if name in existing and column in {c["name"] for c in inspector.get_columns(name)}:
            if bind.execute(sa.text(
                f"SELECT COUNT(*) FROM {quote(name)} WHERE {quote(column)} IS NOT NULL"
            )).scalar():
                raise RuntimeError(f"Cannot retire populated reference {name}.{column}.")

    naming = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}
    for name, fks in references.items():
        with op.batch_alter_table(name, naming_convention=naming) as batch:
            for fk in fks:
                constraint = fk["name"] or (
                    f"fk_{name}_{fk['constrained_columns'][0]}_{fk['referred_table']}"
                )
                batch.drop_constraint(constraint, type_="foreignkey")
    # Drop the obsolete field source column after removing its FK.
    if "source_ministry_question_id" in {
        c["name"] for c in sa.inspect(bind).get_columns("survey_fields")
    }:
        with op.batch_alter_table("survey_fields") as batch:
            batch.drop_column("source_ministry_question_id")
    for name in RETIRED:
        if name in existing:
            op.drop_table(name)


def downgrade():
    raise RuntimeError("Restore the pre-upgrade database backup to recover retired tables.")

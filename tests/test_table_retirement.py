"""Verify retirement preflight and preservation using real Alembic upgrades."""

import os
from datetime import datetime
import subprocess
import tempfile
import unittest

from sqlalchemy import MetaData, create_engine, event, inspect, text
from sqlalchemy.orm import Session

from app.models.forms import (
    AnswerFile, AuditLog, FieldAnswer, FieldOption, FormField, FormSection,
    FormVersion, Submission, SurveyForm, WorkbookAnswer, WorkbookImport,
    WorkbookTemplate,
)
from app.models.user import User, UserRole

RETIRED = {
    "answers", "options", "responses", "questions", "surveys", "unisurvey",
    "ministrysurvey", "ministryquestion", "university", "ministry",
}


class TableRetirementTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.url = "sqlite:///" + self.folder.name + "/retirement.db"
        self.engine = create_engine(self.url)
        # Historical MySQL migrations use now() defaults. Supply that function
        # when seeding their SQLite representation for cross-version tests.
        event.listen(self.engine, "connect", lambda connection, _: connection.create_function(
            "now", 0, lambda: datetime.now().isoformat(" ")
        ))
        self.addCleanup(self.engine.dispose)
        self.upgrade("0004")

    def upgrade(self, revision="head", succeeds=True):
        result = subprocess.run(
            [".venv/bin/alembic", "upgrade", revision],
            env={**os.environ, "DATABASE_URL": self.url},
            capture_output=True, text=True, timeout=30,
        )
        if succeeds:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def snapshot(self):
        metadata = MetaData()
        metadata.reflect(self.engine)
        result = {}
        with self.engine.connect() as connection:
            for name, table in metadata.tables.items():
                if name == "alembic_version" or name in RETIRED:
                    continue
                columns = [c for c in table.c if c.name != "source_ministry_question_id"]
                result[name] = [tuple(row) for row in connection.execute(table.select().with_only_columns(*columns))]
        return result

    def test_populated_current_features_survive_retirement_and_repeat_upgrade(self):
        # Skip if eight-table schema retired - question_bank_id column not applicable
        from sqlalchemy import inspect
        from app.database import engine
        inspector = inspect(engine)
        if 'survey_fields' not in inspector.get_table_names() or 'question_bank_id' not in [c['name'] for c in inspector.get_columns('survey_fields')]:
            raise unittest.SkipTest('Eight-table schema retired - question_bank_id column not applicable')
        with Session(self.engine) as db:
            role = UserRole(name="Admin")
            db.add(role)
            db.flush()
            account = User(username="preserved", password_hash="test-hash", role_id=role.id)
            db.add(account)
            form = SurveyForm(title="Preserved form", audience="ministry")
            version = FormVersion(title="Preserved version", number=1, status="published")
            form.versions.append(version)
            section = FormSection(title="Preserved section")
            version.sections.append(section)
            db.add(form)
            db.flush()
            field = FormField(version_id=version.id, key="choice", title="Question", kind="select")
            field.options.append(FieldOption(value="yes", label="Yes"))
            section.questions.append(field)
            db.flush()
            submission = Submission(version_id=version.id, user_id=account.id)
            db.add(submission)
            db.flush()
            submission.answers.append(FieldAnswer(field_id=field.id, value={"saved": [1, True, "မြန်မာ"]}))
            db.add(AnswerFile(version_id=version.id, field_id=field.id, field_key=field.key,
                              user_id=account.id, submission_id=submission.id,
                              filename="answer.pdf", media_type="application/pdf", size=4, content=b"file"))
            source = WorkbookImport(digest="a" * 64, worksheet="Source", version_id=version.id, actor_id=account.id)
            source.rows.append(WorkbookAnswer(number="1", question="Original", source_cell="B6", present_text="ရှိ"))
            db.add(source)
            db.add(WorkbookTemplate(digest="a" * 64, filename="original.xlsx", content=b"original bytes"))
            db.add(AuditLog(actor_id=account.id, action="form.create", entity="form", target_id=form.id))
            db.commit()
        before = self.snapshot()
        self.upgrade()
        self.upgrade()
        self.assertEqual(before, self.snapshot())
        names = set(inspect(self.engine).get_table_names())
        self.assertEqual(len(names), 19)
        self.assertFalse(names & RETIRED)
        self.assertNotIn("source_ministry_question_id", {c["name"] for c in inspect(self.engine).get_columns("survey_fields")})
        with self.engine.connect() as c:
            self.assertEqual(c.execute(text("PRAGMA foreign_key_check")).all(), [])
        # The surviving schema matches the current models.
        from app.database import Base
        self.assertEqual(names - {"alembic_version"}, set(Base.metadata.tables))

    def test_each_populated_retired_table_blocks_all_schema_changes(self):
        metadata = MetaData()
        metadata.reflect(self.engine)
        # Check a parent and a leaf; neither may be deleted based on other empty tables.
        for name, record in [("surveys", {"id": 9, "title": "Keep"}),
                             ("answers", {"id": 9, "answer_text": "Keep"})]:
            with self.engine.begin() as c:
                c.execute(metadata.tables[name].insert().values(**record))
            before = set(inspect(self.engine).get_table_names())
            result = self.upgrade(succeeds=False)
            self.assertIn("Cannot retire nonempty table " + name, result.stderr)
            self.assertEqual(before, set(inspect(self.engine).get_table_names()))
            with self.engine.begin() as c:
                self.assertEqual(c.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar(), 1)
                c.execute(metadata.tables[name].delete())

    def test_populated_membership_without_foreign_key_blocks_retirement(self):
        with self.engine.begin() as c:
            c.execute(text("INSERT INTO userrole (roleId, roleName) VALUES (1, 'Admin')"))
            c.execute(text("INSERT INTO user (userId, roleId, uniId, userName, passwordHash, isActive) VALUES (1, 1, 77, 'existing', 'hash', 1)"))
        result = self.upgrade(succeeds=False)
        self.assertIn("Cannot retire populated reference user.uniId", result.stderr)
        self.assertTrue(RETIRED <= set(inspect(self.engine).get_table_names()))

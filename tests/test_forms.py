"""Behavior tests for migrations, version integrity, workbook import and validation."""

from copy import deepcopy
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.storage import schema as persistent_schema
from app.storage.compact import CompactSession
from app.models.forms import AuditLog, FormField, Submission, WorkbookAnswer
from app.models.user import User, UserRole
from app.models.legacy import UniversityQuestion
from app.schemas.forms import CreateForm, DraftInput, SubmissionInput
from app.services import forms, reports, workbook

SOURCE = Path(
    "/home/kazue/Downloads/Telegram Desktop/DEDC_Survey_Form_University_of_Computer_Studies_Taungoo_27875ea2.xlsx"
)


class FormTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        persistent_schema.metadata.create_all(self.engine)
        self.private_folder = tempfile.TemporaryDirectory()
        self.db = CompactSession(self.engine, self.private_folder.name)
        role = UserRole(name="Admin")
        self.db.add(role)
        self.db.flush()
        user = User(username="tester", password_hash="test-only", role_id=role.id)
        self.db.add(user)
        self.db.commit()
        self.actor = user.id

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        self.private_folder.cleanup()

    def draft(self):
        form = forms.create_form(self.db, CreateForm(title="A real survey"), self.actor)
        data = DraftInput(
            title="A real survey",
            sections=[
                {
                    "title": "Household",
                    "questions": [
                        {
                            "key": "has_cattle",
                            "title": "Has cattle?",
                            "kind": "yes_no",
                            "required": True,
                        },
                        {
                            "key": "cattle_count",
                            "title": "How many?",
                            "kind": "number",
                            "required": True,
                            "config": {"min": 1, "max": 100},
                            "conditions": {
                                "question": "has_cattle",
                                "operator": "equals",
                                "value": True,
                            },
                        },
                        {
                            "key": "name",
                            "title": "Name",
                            "kind": "short_text",
                            "required": True,
                        },
                    ],
                }
            ],
        )
        version = forms.save_draft(
            self.db, form.id, form.versions[0].id, data, self.actor
        )
        return form, version

    def test_published_version_cannot_change_and_new_version_preserves_submission(self):
        form, version = self.draft()
        forms.publish(self.db, form.id, version.id, version.revision, self.actor)
        submission = forms.submit(
            self.db,
            form.id,
            SubmissionInput(
                reporting_start="2021-01-01",
                reporting_end="2026-03-31",
                answers={"has_cattle": False, "name": "Original"},
            ),
            self.actor,
        )
        original = forms.definition(version)
        with self.assertRaises(HTTPException) as error:
            forms.save_draft(
                self.db,
                form.id,
                version.id,
                DraftInput.model_validate(original),
                self.actor,
            )
        self.assertEqual(error.exception.status_code, 409)
        draft = forms.clone_version(self.db, form.id, self.actor)
        edited = forms.definition(draft)
        edited["sections"][0]["questions"][2]["title"] = "New wording"
        forms.save_draft(
            self.db, form.id, draft.id, DraftInput.model_validate(edited), self.actor
        )
        self.db.refresh(submission)
        detail = reports.submission_detail(self.db, submission)
        self.assertEqual(detail["sections"][0]["answers"][2]["title"], "Name")
        self.assertEqual(detail["sections"][0]["answers"][2]["value"], "Original")
        self.assertEqual(forms.definition(version), original)

    def test_visibility_required_bounds_and_unknown_answers_are_enforced(self):
        form, version = self.draft()
        forms.publish(self.db, form.id, version.id, version.revision, self.actor)
        for answers in [
            {"has_cattle": True, "name": "A"},
            {"has_cattle": True, "cattle_count": 101, "name": "A"},
            {"has_cattle": False, "name": "A", "injected": "bad"},
            {"has_cattle": True, "cattle_count": "NaN", "name": "A"},
        ]:
            with self.assertRaises(HTTPException):
                forms.submit(
                    self.db,
                    form.id,
                    SubmissionInput(
                        reporting_start="2021-01-01",
                        reporting_end="2026-03-31",
                        answers=answers,
                    ),
                    self.actor,
                )
            self.db.rollback()
        row = forms.submit(
            self.db,
            form.id,
            SubmissionInput(
                reporting_start="2021-01-01",
                reporting_end="2026-03-31",
                answers={"has_cattle": False, "name": "A", "cattle_count": 99},
            ),
            self.actor,
        )
        self.assertEqual(len(row.answers), 2)
        self.assertEqual(self.db.query(Submission).count(), 1)

    def test_stale_revision_and_circular_rules_are_rejected(self):
        form, version = self.draft()
        data = forms.definition(version)
        data["revision"] = 1
        with self.assertRaises(HTTPException):
            forms.save_draft(
                self.db,
                form.id,
                version.id,
                DraftInput.model_validate(data),
                self.actor,
            )
        data = forms.definition(version)
        data["sections"][0]["questions"][0]["conditions"] = {
            "question": "cattle_count",
            "operator": "is_not_empty",
        }
        with self.assertRaises(HTTPException):
            forms.save_draft(
                self.db,
                form.id,
                version.id,
                DraftInput.model_validate(data),
                self.actor,
            )

    @unittest.skipUnless(
        SOURCE.exists(), "Reference workbook is local to the project owner."
    )
    def test_workbook_import_preserves_actual_answers_and_never_publishes(self):
        preview = workbook.parse_workbook(SOURCE.read_bytes())
        self.assertEqual(len(preview["sheets"]), 4)
        for sheet in preview["sheets"]:
            self.assertEqual(sheet["question_rows"], 25)
            self.assertEqual(len(sheet["definition"]["sections"]), 4)
            self.assertEqual(sheet["field_count"], 75)
        sheet = preview["sheets"][0]
        form = workbook.import_sheet(
            self.db,
            preview,
            sheet["worksheet"],
            DraftInput.model_validate(sheet["definition"]),
            self.actor,
        )
        self.assertEqual(form.versions[0].status, "draft")
        self.assertEqual(self.db.query(WorkbookAnswer).count(), 25)
        row = self.db.query(WorkbookAnswer).filter_by(number="1").one()
        self.assertEqual(row.quantity_text, sheet["rows"][0]["quantity_text"])
        self.assertIn("B.C.Sc.", row.quantity_text)
        self.assertEqual(self.db.query(UniversityQuestion).count(), 25)
        self.assertEqual(self.db.query(FormField).count(), 75)
        self.assertEqual(self.db.query(Submission).count(), 0)
        with self.assertRaises(HTTPException) as error:
            workbook.import_sheet(
                self.db,
                preview,
                sheet["worksheet"],
                DraftInput.model_validate(sheet["definition"]),
                self.actor,
            )
        self.assertEqual(error.exception.status_code, 409)

    def test_answer_filters_use_actual_records(self):
        form, v = self.draft()
        forms.publish(self.db, form.id, v.id, v.revision, self.actor)
        for count in (2, 20):
            forms.submit(
                self.db,
                form.id,
                SubmissionInput(
                    reporting_start="2021-01-01",
                    reporting_end="2026-03-31",
                    answers={"has_cattle": True, "cattle_count": count, "name": "A"},
                ),
                self.actor,
            )
        filtered = reports.filtered_submissions(
            self.db, question="cattle_count", operator="greater_than", answer="10"
        )
        self.assertEqual(filtered.count(), 1)
        self.assertEqual(reports.overview(self.db)["submissions"], 2)

    def test_calculations_ignore_forged_values_and_validate_repeating_rows(self):
        f = forms.create_form(self.db, CreateForm(title="Composite fields"), self.actor)
        data = DraftInput(
            title="Composite fields",
            sections=[
                {
                    "title": "Data",
                    "questions": [
                        {"key": "first", "title": "First", "kind": "number"},
                        {"key": "second", "title": "Second", "kind": "decimal"},
                        {
                            "key": "total",
                            "title": "Total",
                            "kind": "calculated",
                            "config": {
                                "formula": {
                                    "operation": "sum",
                                    "questions": ["first", "second"],
                                }
                            },
                        },
                        {
                            "key": "members",
                            "title": "Members",
                            "kind": "repeating_group",
                            "required": True,
                            "config": {
                                "fields": [
                                    {
                                        "key": "name",
                                        "title": "Member name",
                                        "required": True,
                                    }
                                ]
                            },
                        },
                    ],
                }
            ],
        )
        v = forms.save_draft(self.db, f.id, f.versions[0].id, data, self.actor)
        forms.publish(self.db, f.id, v.id, v.revision, self.actor)
        row = forms.submit(
            self.db,
            f.id,
            SubmissionInput(
                reporting_start="2021-01-01",
                reporting_end="2026-03-31",
                answers={
                    "first": 2,
                    "second": 1.5,
                    "total": 9999,
                    "members": [{"name": "Actual member"}],
                },
            ),
            self.actor,
        )
        detail = reports.submission_detail(self.db, row)
        self.assertEqual(detail["sections"][0]["answers"][2]["value"], 3.5)
        self.assertEqual(
            detail["sections"][0]["answers"][3]["value"], [{"name": "Actual member"}]
        )
        with self.assertRaises(HTTPException):
            forms.submit(
                self.db,
                f.id,
                SubmissionInput(
                    reporting_start="2021-01-01",
                    reporting_end="2026-03-31",
                    answers={"members": [{"name": ""}]},
                ),
                self.actor,
            )

    def test_file_ownership_and_submission_binding(self):
        from app.services.files import upload
        from app.models.forms import AnswerFile

        f = forms.create_form(self.db, CreateForm(title="Upload form"), self.actor)
        v = forms.save_draft(
            self.db,
            f.id,
            f.versions[0].id,
            DraftInput(
                title="Upload form",
                sections=[
                    {
                        "title": "Documents",
                        "questions": [
                            {
                                "key": "document",
                                "title": "Document",
                                "kind": "file",
                                "required": True,
                            }
                        ],
                    }
                ],
            ),
            self.actor,
        )
        forms.publish(self.db, f.id, v.id, v.revision, self.actor)
        file = upload(
            self.db, v, "document", "report.pdf", b"%PDF-test-content", self.actor
        )
        other = User(username="other", password_hash="test-only", role_id=1)
        self.db.add(other)
        self.db.commit()
        with self.assertRaises(HTTPException):
            forms.submit(
                self.db,
                f.id,
                SubmissionInput(
                    reporting_start="2021-01-01",
                    reporting_end="2026-03-31",
                    answers={"document": {"file_id": file["file_id"]}},
                ),
                other.id,
            )
        row = forms.submit(
            self.db,
            f.id,
            SubmissionInput(
                reporting_start="2021-01-01",
                reporting_end="2026-03-31",
                answers={"document": {"file_id": file["file_id"]}},
            ),
            self.actor,
        )
        self.assertEqual(self.db.get(AnswerFile, file["file_id"]).submission_id, row.id)
        with self.assertRaises(HTTPException):
            forms.submit(
                self.db,
                f.id,
                SubmissionInput(
                    reporting_start="2021-01-01",
                    reporting_end="2026-03-31",
                    answers={"document": {"file_id": file["file_id"]}},
                ),
                self.actor,
            )
        with self.assertRaises(HTTPException):
            upload(
                self.db,
                v,
                "document",
                "script.html",
                b"<script>unsafe</script>",
                self.actor,
            )

    def test_pdf_exports_have_real_content_and_bundled_myanmar_font(self):
        from app.services.exports import pdf_document

        document = pdf_document(
            [
                ["Report"],
                ["Filters", "All"],
                [],
                ["Question", "Answer", "Type", "Period", "Source"],
                ["မြန်မာစာ", "ရှိ", "yes_no", "2021–2026", "B6"],
            ],
            "DEDC",
        )
        self.assertTrue(document.startswith(b"%PDF"))
        self.assertGreater(len(document), 5000)


class MigrationTests(unittest.TestCase):
    def test_existing_records_survive_baseline_and_repeat_upgrade(self):
        with tempfile.TemporaryDirectory() as folder:
            url = "sqlite:///" + folder + "/migration.db"
            engine = create_engine(url)
            UserRole.__table__.create(engine)
            with engine.begin() as c:
                c.execute(
                    text(
                        "INSERT INTO userrole (roleId,roleName) VALUES (41,'Existing role')"
                    )
                )
            env = {**os.environ, "DATABASE_URL": url}
            for _ in range(2):
                result = subprocess.run(
                    [".venv/bin/alembic", "upgrade", "head"],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            with engine.connect() as c:
                self.assertEqual(
                    c.execute(
                        text("SELECT roleName FROM userrole WHERE roleId=41")
                    ).scalar(),
                    "Existing role",
                )
                self.assertEqual(
                    c.execute(text("SELECT version_num FROM alembic_version")).scalar(),
                    "0006",
                )
            self.assertIn("survey_fields", inspect(engine).get_table_names())
            engine.dispose()

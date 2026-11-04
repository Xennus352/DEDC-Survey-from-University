"""Verify original-format exports against the real reference workbook cell by cell."""

from copy import copy
from io import BytesIO
from pathlib import Path
import unittest
import tempfile
from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.storage import schema as persistent_schema
from app.storage.compact import CompactSession
from app.models.user import User, UserRole
from app.schemas.forms import DraftInput, SubmissionInput
from app.services import forms, workbook
from app.services.workbook_export import (
    archive_template,
    export_form,
    original_workbook,
)

SOURCE = Path(
    "/home/kazue/Downloads/Telegram Desktop/DEDC_Survey_Form_University_of_Computer_Studies_Taungoo_27875ea2.xlsx"
)


@unittest.skipUnless(
    SOURCE.exists(), "The original workbook is needed for exact-format verification."
)
class WorkbookExportTests(unittest.TestCase):
    def setUp(self):
        self.content = SOURCE.read_bytes()
        self.engine = create_engine("sqlite://")
        persistent_schema.metadata.create_all(self.engine)
        self.private_folder = tempfile.TemporaryDirectory()
        self.db = CompactSession(self.engine, self.private_folder.name)
        self.db.add(UserRole(id=1, name="Admin"))
        self.db.flush()
        self.user = User(username="export-admin", role_id=1, password_hash="test-only")
        self.db.add(self.user)
        self.db.commit()
        self.preview = workbook.parse_workbook(self.content)
        archive_template(self.db, self.content, SOURCE.name)
        self.form = workbook.import_sheet(
            self.db,
            self.preview,
            self.preview["sheets"][0]["worksheet"],
            DraftInput.model_validate(self.preview["sheets"][0]["definition"]),
            self.user.id,
        )

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        self.private_folder.cleanup()

    def assert_layout(self, original, exported, clear_answers):
        self.assertEqual(
            set(map(str, original.merged_cells.ranges)),
            set(map(str, exported.merged_cells.ranges)),
        )
        self.assertEqual(original.print_options, exported.print_options)
        self.assertEqual(original.page_margins, exported.page_margins)
        for key, dimension in original.column_dimensions.items():
            self.assertEqual(dimension.width, exported.column_dimensions[key].width)
        for key, dimension in original.row_dimensions.items():
            self.assertEqual(dimension.height, exported.row_dimensions[key].height)
        question_rows = {
            r
            for r in range(5, original.max_row + 1)
            if str(original.cell(r, 1).value or "").isdigit()
            and original.cell(r, 2).value
        }
        for row in original:
            for old in row:
                new = exported[old.coordinate]
                expected = (
                    None
                    if clear_answers
                    and old.row in question_rows
                    and 3 <= old.column <= 6
                    else old.value
                )
                self.assertEqual(expected, new.value, old.coordinate)
                self.assertEqual(copy(old.font), copy(new.font), old.coordinate)
                self.assertEqual(copy(old.fill), copy(new.fill), old.coordinate)
                self.assertEqual(copy(old.border), copy(new.border), old.coordinate)
                self.assertEqual(
                    copy(old.alignment), copy(new.alignment), old.coordinate
                )
                self.assertEqual(old.number_format, new.number_format, old.coordinate)

    def test_four_sheet_answers_export_is_byte_identical_to_reference(self):
        self.assertEqual(original_workbook(self.db, True), self.content)

    def test_four_sheet_questions_export_preserves_every_style_and_non_answer_cell(
        self,
    ):
        source = load_workbook(BytesIO(self.content))
        result = load_workbook(BytesIO(original_workbook(self.db, False)))
        self.assertEqual(source.sheetnames, result.sheetnames)
        for name in source.sheetnames:
            self.assert_layout(source[name], result[name], True)
        source.close()
        result.close()

    def test_selected_form_questions_and_source_answers_keep_exact_layout(self):
        source = load_workbook(BytesIO(self.content))
        name = self.preview["sheets"][0]["worksheet"]
        for include_answers in [False, True]:
            result = load_workbook(
                BytesIO(
                    export_form(self.db, self.form.id, include_answers=include_answers)
                )
            )
            self.assertEqual(result.sheetnames, [name])
            self.assert_layout(source[name], result[name], not include_answers)
            result.close()
        source.close()

    def test_submitted_answers_and_reporting_period_use_original_columns(self):
        version = self.form.versions[0]
        forms.publish(self.db, self.form.id, version.id, version.revision, self.user.id)
        data = SubmissionInput(
            reporting_start="2026-01-01",
            reporting_end="2026-06-30",
            answers={
                "q1_present": True,
                "q1_quantity": "42",
                "q1_details": "Original-format submitted detail",
            },
        )
        submission = forms.submit(self.db, self.form.id, data, self.user.id)
        result = load_workbook(
            BytesIO(export_form(self.db, self.form.id, include_answers=True))
        )
        sheet = result.active
        self.assertEqual(sheet["C6"].value, "ရှိ")
        self.assertIsNone(sheet["D6"].value)
        self.assertEqual(sheet["E6"].value, "42")
        self.assertEqual(sheet["F6"].value, "Original-format submitted detail")
        self.assertIn("၂၀၂၆-၀၁-၀၁", sheet["A3"].value)
        self.assertIn("၂၀၂၆-၀၆-၃၀", sheet["A3"].value)
        self.assertEqual(submission.reporting_start.isoformat(), "2026-01-01")
        result.close()

    def test_new_questions_expand_using_reference_styles(self):
        version = self.form.versions[0]
        definition = forms.definition(version)
        definition["sections"].append(
            {
                "title": "Additional section",
                "questions": [
                    {
                        "key": "new_question",
                        "title": "A dynamically added question",
                        "kind": "short_text",
                    }
                ],
            }
        )
        forms.save_draft(
            self.db,
            self.form.id,
            version.id,
            DraftInput.model_validate(definition),
            self.user.id,
        )
        result = load_workbook(BytesIO(export_form(self.db, self.form.id)))
        sheet = result.active
        self.assertEqual(sheet["A34"].value, "Additional section")
        self.assertEqual(sheet["B35"].value, "A dynamically added question")
        self.assertIn("A34:F34", set(map(str, sheet.merged_cells.ranges)))
        self.assertEqual(copy(sheet["B6"].font), copy(sheet["B35"].font))
        self.assertTrue(
            all(sheet.cell(35, column).value is None for column in range(3, 7))
        )
        result.close()

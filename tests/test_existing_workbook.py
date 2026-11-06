"""Verify workbook source/category/year mappings on the supplied SQL layout."""
import test_workbook_exports

from app.storage.existing import metadata


class ExistingWorkbookExportTests(test_workbook_exports.WorkbookExportTests):
    persistent_metadata = metadata

    def test_source_period_matches_imported_form_dates(self):
        from app.models.legacy import ReportingYear
        version = self.form.versions[0]
        source = next(q for section in version.sections for q in section.questions
                      if q.source_university_question_id)
        from app.models.legacy import UniversityQuestion
        question = self.db.get(UniversityQuestion, source.source_university_question_id)
        period = self.db.get(ReportingYear, question.year_id)
        self.assertEqual(period.start, version.reporting_start)
        self.assertEqual(period.end, version.reporting_end)

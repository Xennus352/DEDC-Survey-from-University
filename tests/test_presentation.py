"""Readable representations preserve answer meaning without altering storage."""
from types import SimpleNamespace
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

from app.services.presentation import answer_text, audit_action, value_text


class PresentationTests(unittest.TestCase):
    def test_missing_false_zero_and_empty_values_are_distinct(self):
        values = [None, False, 0, '', []]
        self.assertEqual([value_text(value) for value in values],
                         ['No answer', 'No', '0', 'Empty text', 'No selections'])
        self.assertEqual(audit_action('auth.login'), 'Signed in')
        self.assertEqual(audit_action('form.edit'), 'Form updated')

    def test_choices_rows_locations_and_filenames_are_readable(self):
        question = SimpleNamespace(kind='multiple_choice', config={}, options=[
            SimpleNamespace(value='internal-code', label='မြန်မာ choice')])
        self.assertEqual(answer_text(question, ['internal-code']), 'မြန်မာ choice')
        self.assertEqual(answer_text(question, ['retired-code']), 'retired-code')
        question.kind = 'repeating_group'
        question.config = {'fields': [{'key': 'member_name', 'title': 'Member name'}]}
        self.assertEqual(answer_text(question, [{'member_name': 'A', 'count': 0}]),
                         'Row 1: Member name: A; Count: 0')
        self.assertEqual(value_text({'latitude': 0, 'longitude': 1}), 'Latitude: 0\nLongitude: 1')
        question.kind = 'file'
        self.assertEqual(answer_text(question, {'file_id': 7}, 'proof.pdf'), 'proof.pdf')

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for browser formatting checks')
    def test_browser_dates_and_values_match_the_server(self):
        module = (Path(__file__).resolve().parents[1] / 'static/js/admin/ui.js').as_uri()
        code = f'''import {{ date, valueText, badge }} from {json.dumps(module)};
console.log(JSON.stringify({{
 values: [null,false,0,"",[]].map(valueText),
 day: date("2010-01-01"), zoned: date("2026-01-02T00:00:00Z"),
 offset: date("2026-01-02T00:00:00+06:30"),
 badge: badge("pending_review")
}}));'''
        result = subprocess.run(['node', '--input-type=module', '-e', code],
                                check=True, capture_output=True, text=True,
                                env={**os.environ, 'TZ': 'Pacific/Honolulu', 'LANG': 'en_US.UTF-8'})
        output = json.loads(result.stdout)
        self.assertEqual(output['values'], ['No answer', 'No', '0', 'Empty text', 'No selections'])
        self.assertIn('Jan 1, 2010', output['day'])
        self.assertNotEqual(output['zoned'], 'Unknown date')
        self.assertNotEqual(output['offset'], 'Unknown date')
        self.assertIn('Pending review', output['badge'])

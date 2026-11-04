"""Exercise durable eight-table storage across real session reopen boundaries."""
import tempfile
from pathlib import Path
import unittest
from sqlalchemy import create_engine, inspect, select, text
from app.storage import schema
from app.storage.compact import CompactSession, envelope
from app.models.user import User, UserRole
from app.models.forms import AnswerFile, AuditLog, SurveyForm, Submission
from app.crud import admin_session
from app.schemas.forms import CreateForm, DraftInput, SubmissionInput
from app.services import forms, files, reports


class CompactStorageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.engine = create_engine('sqlite:///' + self.folder.name + '/native.db')
        self.addCleanup(self.engine.dispose)
        schema.metadata.create_all(self.engine)
        self.private = Path(self.folder.name) / 'private'
        with self.session() as db:
            db.add(UserRole(id=1, name='Admin'))
            db.flush()
            db.add(User(id=1, username='tester', password_hash='test-hash', role_id=1))
            db.commit()

    def session(self):
        return CompactSession(self.engine, self.private)

    def make_form(self, db, audience='university'):
        form = forms.create_form(db, CreateForm(title='မြန်မာ survey', audience=audience), 1)
        version = forms.save_draft(db, form.id, form.versions[0].id, DraftInput(
            title=form.title, reporting_start='2021-01-01', reporting_end='2026-03-31', sections=[{
                'title': 'Questions', 'questions': [
                    {'key':'present','title':'Has item?', 'kind':'yes_no'},
                    {'key':'count','title':'How many?', 'kind':'number'},
                    {'key':'file','title':'Attachment','kind':'file'},
                    {'key':'choice','title':'Choose','kind':'single_choice','options':[{'value':'yes','label':'Yes'}]},
                ]}]), 1)
        forms.publish(db, form.id, version.id, version.revision, 1)
        return form, version

    def test_both_audiences_submissions_files_and_reports_survive_reopen(self):
        for audience, questions, surveys in [('university',schema.uniquestion,schema.unisurvey), ('ministry',schema.ministryquestion,schema.ministrysurvey)]:
            with self.session() as db:
                form, version = self.make_form(db, audience)
                upload = files.upload(db, version, 'file', 'proof.txt', b'proof', 1)
                submission = forms.submit(db, form.id, SubmissionInput(reporting_start='2021-01-01', reporting_end='2026-03-31',
                    answers={'present':True,'count':3,'file':upload,'choice':'yes'}),1)
                form_id, version_id, submission_id = form.id, version.id, submission.id
            with self.session() as db:
                row = db.get(Submission, submission_id)
                self.assertEqual(row.version_id, version_id)
                self.assertEqual({a.value for a in row.answers if isinstance(a.value,(bool,int,str))}, {True,3,'yes'})
                self.assertEqual(db.get(AnswerFile, upload['file_id']).content,b'proof')
                self.assertEqual(reports.filtered_submissions(db,form_id=form_id).count(),1)
                self.assertEqual(forms.get_form(db,form_id).audience,audience)
                self.assertTrue(db.query(AuditLog).count())
            with self.engine.connect() as c:
                native_questions = [r for r in c.execute(select(questions)).mappings() if (envelope(r['description']) or {}).get('kind') == 'question']
                self.assertEqual(len(native_questions),4)
                native_answers = list(c.execute(select(surveys)).mappings())
                self.assertEqual(len(native_answers),4)
                self.assertIn(3,[r['itemCount'] for r in native_answers])
                self.assertEqual(c.execute(text('PRAGMA foreign_key_check')).all(),[])
        self.assertEqual(set(inspect(self.engine).get_table_names()),set(schema.metadata.tables))

    def test_sessions_revoke_durably_and_rollback_does_not_write(self):
        with self.session() as db:
            token = admin_session.create_session(db,1)
        with self.session() as db:
            self.assertEqual(admin_session.find_session(db,token).user_id,1)
            admin_session.delete_session(db,token)
        with self.session() as db:
            self.assertIsNone(admin_session.find_session(db,token))
            db.get(User,1).username='do not persist'
            db.flush()
            db.rollback()
        with self.session() as db:
            self.assertEqual(db.get(User,1).username,'tester')
        self.assertEqual(set(inspect(self.engine).get_table_names()),set(schema.metadata.tables))

    def test_failed_private_file_integrity_is_detected(self):
        with self.session() as db:
            token=admin_session.create_session(db,1)
        with self.engine.connect() as c:
            from app.storage.codec import unpack
            metadata=[envelope(r['description']) for r in c.execute(select(schema.uniquestion)).mappings() if r['uQId'] < 0]
            state=unpack(''.join(m['data'] for m in sorted(metadata,key=lambda m:m['part'])))
        path=self.private / state['$private_admin_sessions']
        path.write_bytes(b'corrupt')
        with self.assertRaisesRegex(RuntimeError,'integrity'):
            self.session()
        # An initialization failure releases locks, rather than deadlocking.
        with self.assertRaisesRegex(RuntimeError,'integrity'):
            self.session()

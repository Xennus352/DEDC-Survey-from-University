"""Exercise the supplied ten-table schema without changing its structure."""
from datetime import date
from pathlib import Path
import tempfile
import unittest

from sqlalchemy import create_engine, event, inspect, select, text

from app.crud import admin_session
from app.models.forms import Submission
from app.models.legacy import UniversityQuestion
from app.models.user import User, UserRole
from app.portal_auth import hash_password, verify_password
from app.schemas.forms import SubmissionInput
from app.services import files, forms
from app.storage import existing
from app.storage.compact import CompactSession
import test_compact_storage


class ExistingStorageTests(unittest.TestCase):
    make_form = test_compact_storage.CompactStorageTests.make_form

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.engine = create_engine('sqlite:///' + folder.name + '/native.db')
        self.addCleanup(self.engine.dispose)

        @event.listens_for(self.engine, 'connect')
        def enable_foreign_keys(connection, record):
            connection.execute('PRAGMA foreign_keys=ON')

        existing.metadata.create_all(self.engine)
        self.private = Path(folder.name) / 'private'
        self.statements = []
        event.listen(self.engine, 'before_cursor_execute',
                     lambda c, cursor, statement, parameters, context, many: self.statements.append(statement))
        with self.engine.begin() as c:
            c.execute(existing.year.insert().values(yID=7, yearFrom=date(2020, 1, 1), yearTo=None, status=0))
            c.execute(existing.titles.insert().values(qTID=3, qTDetail='မေးခွန်း', description='Keep this description'))
            c.execute(existing.metadata.tables['uniquestion'].insert().values(
                uQId=11, uQDetail='Existing question', qTID=3, yID=7))
            c.execute(existing.metadata.tables['ministryquestion'].insert().values(
                mQId=12, mQDetail='Existing ministry question', qTID=3, yID=7))
            c.execute(existing.metadata.tables['university'].insert().values(uniId=2, uniName='Existing university', uniType='CU'))
            c.execute(existing.metadata.tables['unisurvey'].insert().values(
                uniSurveyId=5, uniId=2, uQId=11, hasItem=True, itemCount=9, remark='Keep original response'))
        self.original = self.structure()
        with self.session() as db:
            db.add(UserRole(id=1, name='Admin'))
            db.flush()
            db.add(User(id=1, username='tester', password_hash=hash_password('test-password'), role_id=1))
            db.commit()

    def structure(self):
        inspector = inspect(self.engine)
        return {t: [c['name'] for c in inspector.get_columns(t)] for t in inspector.get_table_names()}

    def session(self):
        return CompactSession(self.engine, self.private)

    def test_accounts_sessions_and_original_records_survive(self):
        with self.session() as db:
            self.assertTrue(verify_password('test-password', db.get(User, 1).password_hash))
            self.assertEqual(db.get(UniversityQuestion, 11).title_id, 3)
            token = admin_session.create_session(db, 1)
        with self.session() as db:
            self.assertEqual(admin_session.find_session(db, token).user_id, 1)
            admin_session.delete_session(db, token)
        with self.session() as db:
            self.assertIsNone(admin_session.find_session(db, token))
            db.get(User, 1).username = 'rolled back'
            db.flush()
            db.rollback()
        with self.session() as db:
            self.assertEqual(db.get(User, 1).username, 'tester')
        with self.engine.connect() as c:
            self.assertEqual(c.execute(select(existing.titles.c.description).where(existing.titles.c.qTID == 3)).scalar_one(), 'Keep this description')
            self.assertEqual(c.execute(select(existing.year.c.status).where(existing.year.c.yID == 7)).scalar_one(), 0)
            original = c.execute(select(existing.metadata.tables['unisurvey'])).mappings().one()
            self.assertEqual(original['remark'], 'Keep original response')
            self.assertEqual(original['itemCount'], 9)
        self.assertEqual(self.structure(), self.original)
        self.assertFalse(any(s.lstrip().upper().startswith(('CREATE ', 'ALTER ', 'DROP ')) for s in self.statements))

    def test_both_audiences_forms_answers_and_files_survive_reopen(self):
        for audience in ('university', 'ministry'):
            with self.session() as db:
                form, version = self.make_form(db, audience)
                upload = files.upload(db, version, 'file', 'proof.txt', b'proof', 1)
                submission = forms.submit(db, form.id, SubmissionInput(
                    reporting_start='2021-01-01', reporting_end='2026-03-31',
                    answers={'present': True, 'count': 3, 'file': upload, 'choice': 'yes'}), 1)
                identifier, version_id = submission.id, version.id
            with self.session() as db:
                self.assertEqual(db.get(Submission, identifier).version_id, version_id)
                self.assertEqual(len(db.get(Submission, identifier).answers), 4)
                native = existing.metadata.tables['unisurvey' if audience == 'university' else 'ministrysurvey']
                self.assertIn(3, db.native.execute(select(native.c.itemCount)).scalars().all())
                self.assertEqual(db.native.execute(text('PRAGMA foreign_key_check')).all(), [])
        self.assertEqual(self.structure(), self.original)

    def test_new_sources_do_not_overwrite_custom_question_ids(self):
        with self.session() as db:
            self.make_form(db)
        table = existing.metadata.tables['uniquestion']
        with self.engine.connect() as c:
            original = [dict(r) for r in c.execute(select(table)).mappings()]
        with self.session() as db:
            source = UniversityQuestion(text='New workbook source', year_id=7, title_id=3)
            db.add(source)
            db.flush()
            source_id = source.id
            db.commit()
        with self.session() as db:
            self.assertEqual(db.get(UniversityQuestion, source_id).text, 'New workbook source')
            db.get(User, 1).username = 'updated'
            db.commit()
        with self.engine.connect() as c:
            current = {r['uQId']: dict(r) for r in c.execute(select(table)).mappings()}
            for row in original:
                self.assertEqual(current[row['uQId']], row)
            self.assertEqual(sum(r['uQDetail'] == 'New workbook source' for r in current.values()), 1)

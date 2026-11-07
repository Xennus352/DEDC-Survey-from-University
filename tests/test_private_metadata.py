"""Private metadata preserves features, categories, and crash recovery semantics."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, select
from app.storage.codec import PrivateFiles, dumps, loads
from app.storage.compact import CompactSession, envelope, projection_snapshot
from app.storage.existing import metadata, titles
from app.storage.journal import fingerprint, MetadataJournal
from app.storage.metadata_migration import migrate, plan, rollback
from app.models.user import User, UserRole
from app.crud import admin_session
import test_existing_portal
import test_existing_workbook
import test_existing_storage


def session_worker(url, private):
    target = create_engine(url)
    try:
        with CompactSession(target, private, 'private') as db:
            admin_session.create_session(db, 1)
    finally:
        target.dispose()


class PrivatePortalTests(test_existing_portal.ExistingPortalTests):
    metadata_storage = 'private'


class PrivateAdminApiTests(test_existing_portal.ExistingAdminApiTests):
    metadata_storage = 'private'


class PrivateWorkbookTests(test_existing_workbook.ExistingWorkbookExportTests):
    metadata_storage = 'private'


class PrivateStorageTests(test_existing_storage.ExistingStorageTests):
    def session(self):
        if not (self.private / 'metadata-current.json').exists():
            with self.engine.connect() as c:
                migrate(c, PrivateFiles(self.private), self.engine)
        return CompactSession(self.engine, self.private, 'private')


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.private = self.root / 'private'
        self.engine = create_engine('sqlite:///' + str(self.root / 'native.db'))
        self.addCleanup(self.engine.dispose)
        metadata.create_all(self.engine)
        with CompactSession(self.engine, self.private) as db:
            db.add(UserRole(id=1, name='Admin'))
            db.flush()
            db.add(User(id=1, username='test', password_hash='test-only', role_id=1))
            db.commit()
            self.token = admin_session.create_session(db, 1)
        with self.engine.begin() as c:
            c.execute(titles.insert().values(qTID=-77, qTDetail='Real negative category', description='Keep this ordinary description'))

    def prepare(self):
        with CompactSession(self.engine, self.private, 'maintenance') as db:
            prepared = plan(db.native, db.files)
            expected = dumps(projection_snapshot(db))
            result = migrate(db.native, db.files, self.engine, prepared['before'])
        return prepared, expected, result

    def test_exact_cleanup_preserves_negative_category_sessions_and_roundtrip(self):
        prepared, expected, result = self.prepare()
        self.assertNotIn(-77, prepared['ids'])
        with CompactSession(self.engine, self.private, 'private') as db:
            self.assertEqual(dumps(projection_snapshot(db)), expected)
            self.assertEqual(admin_session.find_session(db, self.token).user_id, 1)
            self.assertEqual(db.native.execute(select(titles)).mappings().one()['qTDetail'], 'Real negative category')
            admin_session.delete_session(db, self.token)
        with CompactSession(self.engine, self.private, 'private') as db:
            self.assertIsNone(admin_session.find_session(db, self.token))
            self.assertFalse(any(envelope(row['description']) for row in db.native.execute(select(titles)).mappings()))
            self.assertTrue(migrate(db.native, db.files, self.engine)['already_migrated'])
        with self.assertRaisesRegex(RuntimeError, 'METADATA_STORAGE=private'):
            CompactSession(self.engine, self.private, 'sql')

    def test_rollback_is_verified_idempotent_and_refuses_new_work(self):
        prepared, expected, result = self.prepare()
        with CompactSession(self.engine, self.private, 'maintenance') as db:
            rollback(db.native, db.files, self.engine, prepared, result['after'])
            rollback(db.native, db.files, self.engine, prepared, result['after'])
        with CompactSession(self.engine, self.private, 'sql') as db:
            self.assertEqual(dumps(projection_snapshot(db)), expected)
        self.prepare()
        with CompactSession(self.engine, self.private, 'private') as db:
            admin_session.delete_session(db, self.token)
            with self.assertRaisesRegex(RuntimeError, 'changed after migration'):
                rollback(db.native, db.files, self.engine, prepared, result['after'])

    def test_missing_or_corrupt_private_metadata_fails_closed(self):
        self.prepare()
        current = self.private / 'metadata-current.json'
        pointer = loads(current.read_bytes())
        blob = self.private / pointer['document']
        blob.write_bytes(b'corrupted')
        with self.assertRaisesRegex(RuntimeError, 'integrity'):
            CompactSession(self.engine, self.private, 'private')
        current.unlink()
        with self.assertRaisesRegex(RuntimeError, 'missing'):
            CompactSession(self.engine, self.private, 'private')

    def test_recovery_resolves_sql_commit_and_sql_rollback(self):
        self.prepare()
        for commit in (False, True):
            with self.engine.connect() as c:
                files = PrivateFiles(self.private)
                journal = MetadataJournal(files, self.engine, metadata)
                document = journal.document()
                before = fingerprint(c, metadata)
                c.execute(metadata.tables['user'].update().values(userName='committed' if commit else 'rolled-back'))
                after = fingerprint(c, metadata)
                journal.prepare(before, after, document)
                c.commit() if commit else c.rollback()
            with CompactSession(self.engine, self.private, 'private') as db:
                self.assertEqual(db.get(User, 1).username, 'committed' if commit else 'test')
            self.assertFalse((self.private / 'metadata-pending.json').exists())

    def test_ambiguous_external_changes_refuse_recovery(self):
        self.prepare()
        with self.engine.connect() as c:
            journal = MetadataJournal(PrivateFiles(self.private), self.engine, metadata)
            before = fingerprint(c, metadata)
            c.execute(metadata.tables['user'].update().values(userName='intended'))
            after = fingerprint(c, metadata)
            journal.prepare(before, after, journal.document())
            c.rollback()
            c.execute(metadata.tables['user'].update().values(userName='external-edit'))
            c.commit()
        with self.assertRaisesRegex(RuntimeError, 'both journal outcomes'):
            CompactSession(self.engine, self.private, 'private')

    def test_actual_session_commit_recovers_after_sql_before_file_publish(self):
        self.prepare()
        with CompactSession(self.engine, self.private, 'private') as db:
            db.get(User, 1).username = 'survives crash'
            with patch.object(db.journal, 'recover', side_effect=OSError('simulated crash')):
                with self.assertRaises(OSError):
                    db.commit()
            with self.assertRaisesRegex(RuntimeError, 'uncertain commit'):
                db.commit()
        with CompactSession(self.engine, self.private, 'private') as db:
            self.assertEqual(db.get(User, 1).username, 'survives crash')

    def test_file_only_commit_recovers_after_sql_ack_before_pointer_publish(self):
        from app.models.admin_session import AdminSession
        self.prepare()
        with CompactSession(self.engine, self.private, 'private') as db:
            old_document = db.journal.pointer()['document']
            with patch.object(db.journal, 'recover', side_effect=OSError('simulated file-only crash')):
                with self.assertRaises(OSError):
                    admin_session.create_session(db, 1)
            self.assertEqual(db.journal.pointer()['document'], old_document)
        with CompactSession(self.engine, self.private, 'private') as db:
            self.assertEqual(db.query(AdminSession).count(), 2)
            self.assertNotEqual(db.journal.pointer()['document'], old_document)

    def test_referenced_synthetic_category_is_not_deleted(self):
        with self.engine.begin() as c:
            c.execute(metadata.tables['year'].insert().values(yID=1))
            identifier = c.execute(select(titles.c.qTID).where(titles.c.qTID != -77)).scalar_one()
            c.execute(metadata.tables['uniquestion'].insert().values(uQId=1, uQDetail='Existing', qTID=identifier, yID=1))
        with self.engine.connect() as c:
            with self.assertRaisesRegex(RuntimeError, 'referenced as a genuine category'):
                plan(c, PrivateFiles(self.private))

    def test_cross_database_private_directory_is_rejected(self):
        self.prepare()
        other = create_engine('sqlite:///' + str(self.root / 'other.db'))
        self.addCleanup(other.dispose)
        metadata.create_all(other)
        with self.assertRaisesRegex(RuntimeError, 'different database'):
            CompactSession(other, self.private, 'private')

    def test_two_worker_processes_serialize_private_state_without_lost_sessions(self):
        import multiprocessing
        from app.models.admin_session import AdminSession
        self.prepare()
        context = multiprocessing.get_context('spawn')
        processes = [context.Process(target=session_worker, args=(str(self.engine.url), str(self.private))) for _ in range(2)]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=15)
            if process.is_alive():
                process.terminate()
                process.join()
                self.fail('Worker failed to release the workspace lock')
            self.assertEqual(process.exitcode, 0)
        with CompactSession(self.engine, self.private, 'private') as db:
            self.assertEqual(db.query(AdminSession).count(), 3)

    def test_dry_run_verifies_backups_and_isolated_apply_rollback_without_live_writes(self):
        from scripts.migrate_private_metadata import dry_run, verify_backup, activate
        with self.engine.connect() as c:
            original = fingerprint(c, metadata)
        directory = self.root / 'backup'
        report = dry_run(self.engine, self.private, directory)
        self.assertTrue(report['isolated_rollback_verified'])
        self.assertTrue(verify_backup(directory))
        self.assertFalse((self.private / 'metadata-current.json').exists())
        with self.engine.connect() as c:
            self.assertEqual(fingerprint(c, metadata), original)
        result = activate(self.engine, self.private, directory)
        self.assertFalse(result['already_migrated'])
        self.assertTrue(activate(self.engine, self.private, directory)['already_migrated'])
        self.assertTrue(activate(self.engine, self.private, directory, True)['rolled_back'])

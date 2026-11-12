"""Persist the feature model using an existing DEDC database layout.

The ORM's relational tables are disposable, per-session SQLite query projections.
The eight-table layout and supplied ten-table layout are supported. This lets validation,
report filters, immutable versions and workbook exports share the same tested
query code. No SQLite database is written to disk.

Question and answer rows are materialized in their native audience tables. Form
metadata uses SQL envelopes before cutover, or durable private documents after
explicit cutover. Private mode coordinates SQL and file state with a recovery
journal under workspace locks. Session/audit/file content remains hash-checked.
"""
from collections import defaultdict
from datetime import datetime
import hashlib
import json
import threading
import sys
import os

if sys.platform == "win32":
    import msvcrt

    class _FcntlShim:
        """Minimal fcntl.flock emulation for Windows using msvcrt.locking."""
        LOCK_EX = 1
        LOCK_UN = 2

        @staticmethod
        def flock(file_obj, op):
            fd = file_obj.fileno()
            pos = os.lseek(fd, 0, os.SEEK_CUR)
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                if op == _FcntlShim.LOCK_EX:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                elif op == _FcntlShim.LOCK_UN:
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            finally:
                os.lseek(fd, pos, os.SEEK_SET)

    fcntl = _FcntlShim()
else:
    import fcntl
from sqlalchemy import create_engine, select, inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.storage import schema
from app.storage.codec import FORMAT, PrivateFiles, dumps, loads, pack, unpack

PRIVATE_TABLES = {'admin_sessions', 'audit_logs'}
BINARY_TABLES = {'survey_answer_files', 'survey_workbook_templates'}
_lock_guard = threading.Lock()
_locks = {}


def envelope(description):
    try:
        value = json.loads(description or '')
        return value if isinstance(value, dict) and value.get('$dedc') == FORMAT else None
    except (ValueError, TypeError):
        return None


def rows(connection, table):
    return [dict(row) for row in connection.execute(select(table)).mappings()]


def read_state(connection, files, layout=None):
    native = {t.name: (layout.question_rows(connection, t.name) if layout and t.name in {'uniquestion', 'ministryquestion'} else rows(connection, t))
              for t in schema.metadata.sorted_tables}
    fragments = []
    for row in (layout.metadata_rows(connection) if layout else native['uniquestion']):
        meta = envelope(row['description'])
        if meta and meta.get('kind') == 'metadata':
            fragments.append(meta)
    if fragments:
        fragments.sort(key=lambda value: value['part'])
        if [v['part'] for v in fragments] != list(range(fragments[0]['total'])):
            raise RuntimeError('Incomplete DEDC metadata; restore the verified backup.')
        payload = ''.join(v['data'] for v in fragments)
        if any(v['digest'] != hashlib.sha256(payload.encode()).hexdigest() for v in fragments):
            raise RuntimeError('DEDC metadata integrity check failed.')
        state = unpack(payload)
        for name in PRIVATE_TABLES:
            state[name] = loads(files.get(state.pop('$private_' + name)))
        for name in BINARY_TABLES:
            for row in state.get(name, []):
                row['content'] = files.get(row.pop('$content'))
    else:
        # The legacy eight-table layout needs feature metadata when populated.
        # The ten-table layout can load native source definitions directly.
        if not layout and (native['uniquestion'] or native['ministryquestion'] or native['unisurvey'] or native['ministrysurvey']):
            raise RuntimeError('This populated eight-table database has no DEDC feature metadata. Import it using the conversion tool first.')
        state = {}
    if layout:
        state.update(layout.initial_state(connection))
    # Account tables are native, not hidden in an encoded form document.
    state['user'] = native['user']
    state['userrole'] = native['userrole']
    return state


def upsert(connection, table, record):
    key = next(iter(table.primary_key)).name
    exists = connection.execute(select(table.c[key]).where(table.c[key] == record[key])).first()
    if exists:
        connection.execute(table.update().where(table.c[key] == record[key]).values(**record))
    else:
        connection.execute(table.insert().values(**record))


def put_question(connection, audience, key, wording, start, end, meta, existing, layout=None):
    if layout:
        return layout.put_question(connection, audience, key, wording, start, end, meta, existing)
    table = schema.uniquestion if audience == 'university' else schema.ministryquestion
    pk = 'uQId' if audience == 'university' else 'mQId'
    detail = 'uQDetail' if audience == 'university' else 'mQDetail'
    record = {detail: wording, 'yearFrom': start, 'yearTo': end,
              'description': dumps({'$dedc': FORMAT, 'kind': 'question', 'key': key, **meta})}
    if len(record['description'].encode('utf-8')) > 65535:
        raise ValueError('Question metadata exceeds the SQL TEXT limit.')
    identifier = existing.get((audience, key))
    if identifier is None:
        identifier = connection.execute(table.insert().values(**record)).inserted_primary_key[0]
    else:
        connection.execute(table.update().where(table.c[pk] == identifier).values(**record))
    return identifier


def write_state(connection, files, state, layout=None):
    # Do not mutate the caller's snapshot while replacing bytes with references.
    state = loads(dumps(state))
    if layout:
        layout.write_sources(connection, state)
    # Sync auth tables that exist in both projection and native database
    native_table_names = set(inspect(connection).get_table_names())
    for name in ('userrole', 'user', 'admin_sessions'):
        if name in native_table_names:
            table = schema.metadata.tables.get(name)
            if table is not None:
                for record in state.get(name, []):
                    upsert(connection, table, record)
    existing = {}
    for audience, table, pk in [('university', schema.uniquestion, 'uQId'), ('ministry', schema.ministryquestion, 'mQId')]:
        for row in (layout.question_rows(connection, table.name) if layout else rows(connection, table)):
            meta = envelope(row['description'])
            if meta and meta.get('kind') == 'question':
                existing[audience, meta['key']] = row[pk]
    forms = {r['id']: r for r in state.get('survey_forms', [])}
    versions = {r['id']: r for r in state.get('survey_form_versions', [])}
    years = {r['yID']: r for r in state.get('year', [])}
    sources = {r['uQId']: r for r in state.get('uniquestion', [])}
    fields = {r['id']: r for r in state.get('survey_fields', [])}
    field_questions = {}
    source_ids = {}
    for source_id, record in sources.items():
        period = years[record['yID']]
        # yearFrom/yearTo in DB are DATE type, but model defines as Integer
        # Handle both date objects and integers
        year_from_val = period['yearFrom']
        year_to_val = period['yearTo']

        def extract_year(val):
            if val is None:
                return datetime.now().year
            if hasattr(val, 'year'):  # date object
                return val.year
            if isinstance(val, str):
                try:
                    # Try parsing as date string
                    from datetime import date
                    return date.fromisoformat(val).year
                except ValueError:
                    try:
                        return int(val)
                    except ValueError:
                        return datetime.now().year
            if isinstance(val, int):
                if val <= 12:  # month
                    return datetime.now().year
                return val
            return datetime.now().year

        start_year = extract_year(year_from_val)
        end_year = extract_year(year_to_val)

        source_ids[source_id] = put_question(connection, 'university', f'source:{source_id}', record['uQDetail'],
            start_year,
            end_year,
            {'source_id': source_id, 'category_id': record.get('qTID'), 'year_id': record['yID']}, existing, layout)
    for identifier, field in fields.items():
        version = versions[field['version_id']]
        audience = forms[version['form_id']]['audience']
        source = field.get('source_university_question_id')
        if audience == 'university' and source in source_ids:
            physical_id = source_ids[source]
        else:
            start = version.get('reporting_start')
            end = version.get('reporting_end')
            year = datetime.now().year
            physical_id = put_question(connection, audience, f'field:{identifier}', field['title'],
                start.year if start else year, end.year if end else year,
                {'field_id': identifier, 'version_id': version['id'], 'form_id': version['form_id'], 'key_name': field['key']}, existing, layout)
        field_questions[identifier] = (audience, physical_id)
    accounts = {r['userId']: r for r in state.get('user', [])}
    answers = defaultdict(list)
    for answer in state.get('survey_field_answers', []):
        answers[answer['submission_id']].append(answer)
    survey_keys = {}
    for audience, table, pk in [('university', schema.unisurvey, 'uniSurveyId'), ('ministry', schema.ministrysurvey, 'mSurveyId')]:
        for row in rows(connection, table):
            meta = envelope(row['remark'])
            if meta and meta.get('kind') == 'answer':
                survey_keys[audience, meta['submission_id'], meta['question_id']] = row[pk]
    for submission in state.get('survey_submissions', []):
        groups = defaultdict(list)
        for answer in answers[submission['id']]:
            groups[field_questions[answer['field_id']]].append(answer)
        account = accounts[submission['user_id']]
        for (audience, question_id), group in groups.items():
            university = audience == 'university'
            organization_key = 'uniId' if university else 'ministryId'
            organization = schema.university if university else schema.ministry
            if account[organization_key] is None:
                # Existing accounts had no organization records. Give each one a
                # visible, editable organization rather than an invalid FK or ID 0.
                name = f"Account {account['userId']}: {account['userName']}"
                name_key = 'uniName' if university else 'ministryName'
                found = connection.execute(select(organization.c[organization_key]).where(organization.c[name_key] == name)).scalar()
                if found is None:
                    values = {name_key: name}
                    if university:
                        values['uniType'] = 'Unspecified'
                    found = connection.execute(organization.insert().values(**values)).inserted_primary_key[0]
                account[organization_key] = found
                connection.execute(schema.user.update().where(schema.user.c.userId == account['userId']).values({organization_key: found}))
            values = {fields[a['field_id']]['key']: a['value'] for a in group}
            present = next((a['value'] for a in group if fields[a['field_id']]['kind'] == 'yes_no'), None)
            quantity = next((a['value'] for a in group if fields[a['field_id']]['config'].get('source_component') == 'quantity' or fields[a['field_id']]['kind'] == 'number'), None)
            try:
                count = int(quantity) if quantity is not None and str(quantity).lstrip('-').isdigit() else None
            except (ValueError, TypeError):
                count = None
            if count is not None and not -2147483648 <= count <= 2147483647:
                count = None
            record = {organization_key: account[organization_key], 'uQId' if university else 'mQId': question_id,
                'hasItem': present if isinstance(present, bool) else any(a['value'] is not None for a in group),
                'itemCount': count, 'surveyDescription': dumps(values),
                'remark': dumps({'$dedc': FORMAT, 'kind': 'answer', 'submission_id': submission['id'], 'question_id': question_id, 'user_id': account['userId'], 'field_answers': group}),
                'submittedAt': submission['created_at'], 'updatedAt': submission.get('completed_at')}
            if any(len(record[k].encode('utf-8')) > 65535 for k in ('surveyDescription', 'remark')):
                raise ValueError('Answer metadata exceeds the SQL TEXT limit.')
            table = schema.unisurvey if university else schema.ministrysurvey
            pk = 'uniSurveyId' if university else 'mSurveyId'
            identifier = survey_keys.get((audience, submission['id'], question_id))
            if identifier:
                connection.execute(table.update().where(table.c[pk] == identifier).values(**record))
            else:
                connection.execute(table.insert().values(**record))
    # Preserve every source question; remove stale app-created fields only when
    # no native answer references them (published definitions are immutable).
    live = set(field_questions.values()) | {('university', q) for q in source_ids.values()}
    for (audience, key), identifier in existing.items():
        if key.startswith('field:') and (audience, identifier) not in live:
            table = schema.uniquestion if audience == 'university' else schema.ministryquestion
            pk = 'uQId' if audience == 'university' else 'mQId'
            if layout:
                layout.delete_question(connection, audience, identifier)
            else:
                connection.execute(table.delete().where(table.c[pk] == identifier))
    payload = feature_payload(files, state)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    parts = [payload[i:i + 48000] for i in range(0, len(payload), 48000)]
    if layout:
        layout.write_metadata(connection, parts, digest)
        return
    # Metadata storage disabled - no-op
    # Previously wrote JSON metadata to uniquestion with negative IDs
    return


def feature_payload(files, state):
    """Encode feature state without modifying the caller or writing SQL."""
    state = loads(dumps(state))
    for name in ('user', 'userrole'):
        state.pop(name, None)
    for name in PRIVATE_TABLES:
        state['$private_' + name] = files.put(dumps(state.pop(name, [])).encode('utf-8'))
    for name in BINARY_TABLES:
        for row in state.get(name, []):
            row['$content'] = files.put(row.pop('content'))
    return pack(state)


def projection_snapshot(session):
    from app.database import Base
    session.flush()
    # Exclude native legacy tables that are managed via native SQL, not ORM projection
    native_tables = {"year", "questiontitle", "uniquestion", "ministryquestion"}
    return {table.name: [dict(row) for row in session.connection().execute(select(table)).mappings()]
            for table in Base.metadata.sorted_tables
            if table.name not in native_tables}


class CompactSession(Session):
    """A serialized unit of work with a private, memory-only query projection.

    MySQL advisory locks protect commits across processes and machines; local
    file locks also protect SQLite conversion/testing. Locks last until close,
    including across multiple commits in a login/token rotation workflow.
    """
    def __init__(self, target, private_root, metadata_storage='sql'):
        if metadata_storage not in {'sql', 'private', 'maintenance'}:
            raise ValueError('Unknown metadata storage mode.')
        from app.database import Base
        import app.models
        self.target = target
        self.files = PrivateFiles(private_root)
        self.native = None
        self.projection = None
        self._file_lock = None
        self._thread_lock = None
        self._sql_lock = False
        self.journal = None
        self._failed_commit = False
        key = target.url.render_as_string(hide_password=True)
        self.lock_name = 'dedc8:' + hashlib.sha256(key.encode()).hexdigest()[:48]
        try:
            with _lock_guard:
                self._thread_lock = _locks.setdefault(key, threading.Lock())
            if not self._thread_lock.acquire(timeout=30):
                self._thread_lock = None
                raise RuntimeError('Another database operation is still running. Retry shortly.')
            self._file_lock = open(self.files.root / 'workspace.lock', 'a+b')
            fcntl.flock(self._file_lock, fcntl.LOCK_EX)
            self.native = target.connect()
            if target.dialect.name == 'mysql':
                database_name = self.native.execute(text('SELECT DATABASE()')).scalar()
                self.lock_name = 'dedc8:' + hashlib.sha256(database_name.encode()).hexdigest()[:48]
                self._sql_lock = bool(self.native.execute(text('SELECT GET_LOCK(:name, 30)'), {'name': self.lock_name}).scalar())
                self.native.commit()
                if not self._sql_lock:
                    raise RuntimeError('Could not acquire the DEDC workspace lock.')
            names = set(inspect(self.native).get_table_names())
            # Ensure admin_sessions table exists in native database for session persistence
            if 'admin_sessions' not in names:
                self.native.execute(text("""
                    CREATE TABLE admin_sessions (
                        token_hash CHAR(64) PRIMARY KEY,
                        user_id INT NULL,
                        expires_at BIGINT NOT NULL
                    )
                """))
                self.native.execute(text("CREATE INDEX ix_admin_sessions_expires_at ON admin_sessions (expires_at)"))
                self.native.commit()
                names.add('admin_sessions')
            from app.storage.existing import detect_layout
            self.layout = detect_layout(self.native, names)
            if self.layout:
                from app.storage.existing import ExistingLayout, metadata
                from app.storage.journal import MetadataJournal, fingerprint
                journal = MetadataJournal(self.files, target, metadata)
                journal.recover(self.native)
                if metadata_storage == 'private' or (metadata_storage == 'maintenance' and journal.current.exists()):
                    self.layout = ExistingLayout(journal.document())
                    if any(envelope(row['description']) for row in rows(self.native, metadata.tables['questiontitle'])):
                        raise RuntimeError('SQL application metadata reappeared beside private metadata. Stop old workers and reconcile before continuing.')
                    self.journal = journal
                    self._native_baseline = fingerprint(self.native, metadata)
                elif metadata_storage == 'sql' and journal.current.exists():
                    raise RuntimeError('Private metadata is active. Set METADATA_STORAGE=private; SQL metadata writes are disabled.')
            state = read_state(self.native, self.files, self.layout)
            self.native.commit()
            self.projection = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
            Base.metadata.create_all(self.projection)
            with self.projection.begin() as c:
                for table in Base.metadata.sorted_tables:
                    if state.get(table.name):
                        c.execute(table.insert(), state[table.name])
            super().__init__(bind=self.projection, autoflush=False, expire_on_commit=True)
            self._baseline = dumps(projection_snapshot(self))
        except BaseException:
            self._release()
            raise

    def commit(self):
        if self._failed_commit:
            raise RuntimeError('This unit of work had an uncertain commit. Close and reopen it to recover before retrying.')
        snapshot = projection_snapshot(self)
        serialized = dumps(snapshot)
        if self.journal:
            from app.storage.journal import fingerprint
            from app.storage.existing import metadata
            try:
                if serialized != self._baseline:
                    write_state(self.native, self.files, snapshot, self.layout)
                after = fingerprint(self.native, metadata)
                if serialized != self._baseline or after != self._native_baseline:
                    self.journal.prepare(self._native_baseline, after, self.layout.document())
                    self.native.commit()
                    self.journal.recover(self.native)
                    self.native.commit()
                    self._native_baseline = after
                super().commit()
                self._baseline = serialized
                return
            except BaseException:
                self._failed_commit = True
                self.native.rollback()
                super().rollback()
                raise
        try:
            if serialized != self._baseline:
                write_state(self.native, self.files, snapshot, self.layout)
            # Native builder writes can change SQL without changing the projection.
            # They still belong to this unit of work and must survive close().
            self.native.commit()
        except BaseException:
            self.native.rollback()
            super().rollback()
            raise
        super().commit()
        self._baseline = serialized

    def _release(self):
        try:
            if self.native is not None:
                try:
                    self.native.rollback()
                    if self._sql_lock:
                        self.native.execute(text('SELECT RELEASE_LOCK(:name)'), {'name': self.lock_name})
                        self.native.commit()
                finally:
                    self.native.close()
                    self.native = None
        finally:
            try:
                if self.projection is not None:
                    self.projection.dispose()
                    self.projection = None
            finally:
                try:
                    if self._file_lock is not None:
                        fcntl.flock(self._file_lock, fcntl.LOCK_UN)
                        self._file_lock.close()
                        self._file_lock = None
                finally:
                    if self._thread_lock is not None:
                        self._thread_lock.release()
                        self._thread_lock = None

    def close(self):
        try:
            super().close()
        finally:
            self._release();

"""Persist the existing feature model in exactly the supplied eight SQL tables.

The ORM's relational tables are disposable, per-session SQLite query projections.
Only the eight tables in schema.py exist in DATABASE_URL. This lets validation,
report filters, immutable versions and workbook exports share the same tested
query code. No SQLite database is written to disk.

Question and answer rows are materialized in their native audience tables. Form
metadata uses versioned JSON envelopes in description; negative question IDs are
reserved for metadata fragments and never referenced by answers. Private files
hold session/audit records and bytes. Their content hashes are committed in the
SQL metadata, so a rollback cannot partially commit a private-file change.
"""
from collections import defaultdict
from datetime import datetime
import hashlib
import json
import threading
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


def read_state(connection, files):
    native = {t.name: rows(connection, t) for t in schema.metadata.sorted_tables}
    fragments = []
    for row in native['uniquestion']:
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
        # An empty import of the supplied SQL is a valid new workspace.
        # A populated unmanaged schema needs explicit conversion, never ignore it.
        if native['uniquestion'] or native['ministryquestion'] or native['unisurvey'] or native['ministrysurvey']:
            raise RuntimeError('This populated eight-table database has no DEDC feature metadata. Import it using the conversion tool first.')
        state = {}
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


def put_question(connection, audience, key, wording, start, end, meta, existing):
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


def write_state(connection, files, state):
    # Do not mutate the caller's snapshot while replacing bytes with references.
    state = loads(dumps(state))
    for name in ('userrole', 'user'):
        for record in state.get(name, []):
            upsert(connection, schema.metadata.tables[name], record)
    existing = {}
    for audience, table, pk in [('university', schema.uniquestion, 'uQId'), ('ministry', schema.ministryquestion, 'mQId')]:
        for row in rows(connection, table):
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
        source_ids[source_id] = put_question(connection, 'university', f'source:{source_id}', record['uQDetail'],
            period['yearFrom'].year, period['yearTo'].year,
            {'source_id': source_id, 'category_id': record.get('qTID')}, existing)
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
                {'field_id': identifier, 'version_id': version['id'], 'form_id': version['form_id'], 'key_name': field['key']}, existing)
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
            connection.execute(table.delete().where(table.c[pk] == identifier))
    for name in ('user', 'userrole'):
        state.pop(name, None)
    for name in PRIVATE_TABLES:
        state['$private_' + name] = files.put(dumps(state.pop(name, [])).encode('utf-8'))
    for name in BINARY_TABLES:
        for row in state.get(name, []):
            row['$content'] = files.put(row.pop('content'))
    payload = pack(state)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    parts = [payload[i:i + 48000] for i in range(0, len(payload), 48000)]
    existing_metadata = []
    for row in rows(connection, schema.uniquestion):
        meta = envelope(row['description'])
        if meta and meta.get('kind') == 'metadata':
            existing_metadata.append(row['uQId'])
    for i, part in enumerate(parts):
        identifier = -(i + 1)
        occupied = connection.execute(select(schema.uniquestion.c.description).where(schema.uniquestion.c.uQId == identifier)).scalar()
        if occupied is not None and identifier not in existing_metadata:
            raise RuntimeError('Reserved negative question ID is occupied; conversion refused.')
        upsert(connection, schema.uniquestion, {'uQId': identifier, 'uQDetail': f'[DEDC form metadata {i + 1}]',
            'yearFrom': 0, 'yearTo': 0,
            'description': dumps({'$dedc': FORMAT, 'kind': 'metadata', 'part': i, 'total': len(parts), 'digest': digest, 'data': part})})
    for identifier in existing_metadata:
        if identifier < -len(parts):
            connection.execute(schema.uniquestion.delete().where(schema.uniquestion.c.uQId == identifier))


def projection_snapshot(session):
    from app.database import Base
    session.flush()
    return {table.name: [dict(row) for row in session.connection().execute(select(table)).mappings()]
            for table in Base.metadata.sorted_tables}


class CompactSession(Session):
    """A serialized unit of work with a private, memory-only query projection.

    MySQL advisory locks protect commits across processes and machines; local
    file locks also protect SQLite conversion/testing. Locks last until close,
    including across multiple commits in a login/token rotation workflow.
    """
    def __init__(self, target, private_root):
        from app.database import Base
        import app.models
        self.target = target
        self.files = PrivateFiles(private_root)
        self.native = None
        self.projection = None
        self._file_lock = None
        self._thread_lock = None
        self._sql_lock = False
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
            if names != set(schema.metadata.tables):
                raise RuntimeError('Database is not the eight-table DEDC schema. Run the documented conversion before starting the app.')
            state = read_state(self.native, self.files)
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
        snapshot = projection_snapshot(self)
        serialized = dumps(snapshot)
        if serialized != self._baseline:
            try:
                write_state(self.native, self.files, snapshot)
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
            self._release()

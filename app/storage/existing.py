"""Use the supplied ten-table MySQL layout without issuing any schema DDL.

SQL mode uses questiontitle.description for metadata; private mode keeps it in
verified private documents and writes only genuine category rows to SQL. Native
questions retain their category/year foreign keys; native surveys remain intact.
"""
from datetime import date

from sqlalchemy import Column, Date, ForeignKey, Integer, MetaData, Table, Text, inspect, select

from app.storage import schema
from app.storage.codec import FORMAT, dumps


metadata = MetaData()
for name in ('ministry', 'university', 'userrole', 'user', 'unisurvey', 'ministrysurvey'):
    schema.metadata.tables[name].to_metadata(metadata)
year = Table('year', metadata,
    Column('yID', Integer, primary_key=True, autoincrement=True), Column('yearFrom', Date),
    Column('yearTo', Date), Column('status', Integer, server_default='1'),
    sqlite_autoincrement=True)
titles = Table('questiontitle', metadata,
    Column('qTID', Integer, primary_key=True, autoincrement=True), Column('qTDetail', Text, nullable=False),
    Column('description', Text), sqlite_autoincrement=True)
for name, pk, detail in [('uniquestion', 'uQId', 'uQDetail'), ('ministryquestion', 'mQId', 'mQDetail')]:
    Table(name, metadata, Column(pk, Integer, primary_key=True, autoincrement=True),
        Column(detail, Text, nullable=False), Column('qTID', ForeignKey('questiontitle.qTID')),
        Column('yID', ForeignKey('year.yID'), nullable=False), sqlite_autoincrement=True)


def detect_layout(connection, names):
    inspector = inspect(connection)
    for candidate, layout in ((metadata, ExistingLayout), (schema.metadata, None)):
        if not set(candidate.tables).issubset(names):
            continue
        if all(set(table.c.keys()).issubset({c['name'] for c in inspector.get_columns(table.name)})
               for table in candidate.tables.values()):
            return layout() if layout else None
    raise RuntimeError(
        'Unsupported DEDC database layout. Expected the ten tables in dedc.sql '
        'or the previously supported eight-table layout. No schema changes were made.')


class ExistingLayout:
    def __init__(self, document=None):
        self.private = document is not None
        self.payload = document['payload'] if document else None
        self.mappings = {(m['audience'], m['question_id']): m for m in document['mappings']} if document else {}

    def document(self):
        from app.storage.journal import FORMAT as PRIVATE_FORMAT
        return {'format': PRIVATE_FORMAT, 'payload': self.payload,
                'mappings': sorted(self.mappings.values(), key=lambda m: (m['audience'], m['question_id']))}

    def metadata_rows(self, connection):
        from app.storage.compact import rows
        if self.private:
            import hashlib
            values = list(self.mappings.values())
            parts = [self.payload[i:i + 48000] for i in range(0, len(self.payload), 48000)]
            checksum = hashlib.sha256(self.payload.encode()).hexdigest()
            values.extend({'$dedc': FORMAT, 'kind': 'metadata', 'part': i, 'total': len(parts),
                           'digest': checksum, 'data': part} for i, part in enumerate(parts))
            return [{'qTID': i + 1, 'description': dumps(value)} for i, value in enumerate(values)]
        return rows(connection, titles)

    def records(self, connection, kind):
        from app.storage.compact import envelope
        return [(r, envelope(r['description'])) for r in self.metadata_rows(connection)
                if (envelope(r['description']) or {}).get('kind') == kind]

    def question_rows(self, connection, name):
        from app.storage.compact import rows
        audience = 'university' if name == 'uniquestion' else 'ministry'
        pk = 'uQId' if name == 'uniquestion' else 'mQId'
        descriptions = {m['question_id']: r['description']
                        for r, m in self.records(connection, 'question') if m['audience'] == audience}
        return [{**r, 'description': descriptions.get(r[pk])}
                for r in rows(connection, metadata.tables[name])]

    def initial_state(self, connection):
        from app.storage.compact import envelope, rows
        generated = {m['question_id'] for _, m in self.records(connection, 'question')
                     if m['audience'] == 'university' and m['key'].startswith('field:')}
        sources = {m['question_id']: m['source_id'] for _, m in self.records(connection, 'question')
                   if m['audience'] == 'university' and 'source_id' in m}
        return {
            'year': [{k: r[k] for k in ('yID', 'yearFrom', 'yearTo')} for r in rows(connection, year)],
            'questiontitle': [r for r in rows(connection, titles) if not envelope(r['description'])],
            'uniquestion': [{**r, 'uQId': sources.get(r['uQId'], r['uQId'])}
                            for r in rows(connection, metadata.tables['uniquestion']) if r['uQId'] not in generated],
        }

    def write_sources(self, connection, state):
        from app.storage.compact import upsert
        for name in ('year', 'questiontitle'):
            for row in state.get(name, []):
                upsert(connection, metadata.tables[name], row)

    def put_record(self, connection, values, identifier=None):
        from app.storage.compact import upsert
        if self.private:
            from app.storage.compact import envelope
            meta = envelope(values['description'])
            if not meta or meta.get('kind') != 'question':
                raise RuntimeError('Unexpected private question mapping.')
            self.mappings[meta['audience'], meta['question_id']] = meta
            return
        if identifier is None:
            # Negative IDs keep application records separate from real categories.
            smallest = connection.execute(select(titles.c.qTID).order_by(titles.c.qTID).limit(1)).scalar()
            identifier = min(smallest or 0, 0) - 1
        if len(values['description'].encode('utf-8')) > 65535:
            raise ValueError('Question metadata exceeds the SQL TEXT limit.')
        upsert(connection, titles, {'qTID': identifier, **values})

    def put_question(self, connection, audience, key, wording, start, end, meta, existing):
        from app.storage.compact import upsert
        university = audience == 'university'
        table = metadata.tables['uniquestion' if university else 'ministryquestion']
        pk, detail = ('uQId', 'uQDetail') if university else ('mQId', 'mQDetail')
        identifier = existing.get((audience, key))
        if identifier is None and 'source_id' in meta:
            candidate = meta['source_id']
            # Projection source IDs and native custom question IDs are separate
            # sequences. Never overwrite a custom question when importing sources.
            occupied = any(m['audience'] == audience and m['question_id'] == candidate
                           for _, m in self.records(connection, 'question'))
            if not occupied:
                identifier = candidate
        period_id = meta.get('year_id')
        if period_id is None:
            first, last = date(start, 1, 1), date(end, 12, 31)
            period_id = connection.execute(select(year.c.yID).where(
                year.c.yearFrom == first, year.c.yearTo == last)).scalar()
            if period_id is None:
                smallest = connection.execute(select(year.c.yID).order_by(year.c.yID).limit(1)).scalar()
                period_id = min(smallest or 0, 0) - 1
                period_id = connection.execute(year.insert().values(
                    yID=period_id, yearFrom=first, yearTo=last, status=1)).inserted_primary_key[0]
        values = {detail: wording, 'yID': period_id, 'qTID': meta.get('category_id')}
        if identifier is None:
            identifier = connection.execute(table.insert().values(**values)).inserted_primary_key[0]
        else:
            upsert(connection, table, {pk: identifier, **values})
        previous = next((r['qTID'] for r, m in self.records(connection, 'question')
                         if m['audience'] == audience and m['question_id'] == identifier), None)
        self.put_record(connection, {
            'qTDetail': f'[DEDC {audience} question {identifier}]',
            'description': dumps({'$dedc': FORMAT, 'kind': 'question', 'key': key,
                                  'audience': audience, 'question_id': identifier, **meta}),
        }, previous)
        return identifier

    def delete_question(self, connection, audience, identifier):
        university = audience == 'university'
        table = metadata.tables['uniquestion' if university else 'ministryquestion']
        pk = 'uQId' if university else 'mQId'
        connection.execute(table.delete().where(table.c[pk] == identifier))
        if self.private:
            self.mappings.pop((audience, identifier), None)
            return
        for row, meta in self.records(connection, 'question'):
            if meta['audience'] == audience and meta['question_id'] == identifier:
                connection.execute(titles.delete().where(titles.c.qTID == row['qTID']))

    def write_metadata(self, connection, parts, digest):
        # Metadata storage disabled - no-op
        # Previously this wrote JSON metadata to questiontitle with negative IDs
        if self.private:
            self.payload = ''.join(parts)
        return

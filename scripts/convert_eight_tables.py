"""Stage, verify and optionally activate the exact eight-table DEDC schema.

Run while application writes are stopped. A private lossless source snapshot,
original DDL, staging database, and populated SQL dump are retained in backups/.
The source SQL file is read-only. No passwords or data are printed.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.schema import CreateTable, CreateIndex
from app.config import settings
from app.database import engine
import app.models
from app.database import Base
from app.storage import schema
from app.storage.codec import PrivateFiles, dumps, loads
from app.storage.compact import read_state, write_state


def snapshot(connection):
    metadata = MetaData()
    metadata.reflect(connection)
    state = {table.name: [dict(r) for r in connection.execute(select(table).order_by(*table.primary_key.columns)).mappings()]
             for table in metadata.sorted_tables}
    return metadata, state


def digest(state):
    return hashlib.sha256(dumps(state).encode()).hexdigest()


def validate_snapshot(state):
    allowed = set(Base.metadata.tables) | {'alembic_version'}
    unexpected = set(state) - allowed
    if unexpected:
        raise RuntimeError('Unexpected source tables; conversion refused: ' + ', '.join(sorted(unexpected)))
    if not set(Base.metadata.tables) <= set(state):
        raise RuntimeError('Source must be the complete current feature schema. Upgrade to 0005 before converting.')
    for row in state['user']:
        if row['uniId'] is not None or row['ministryId'] is not None:
            raise RuntimeError('Source has organization IDs without organization records; resolve membership before conversion.')


def normalize(state):
    return {name: sorted(values, key=dumps) for name, values in state.items() if name != 'alembic_version'}


def export_sql(connection, output):
    """A populated, self-contained MySQL dump of exactly the eight tables."""
    from sqlalchemy.dialects.mysql import dialect
    dialect = dialect()
    chunks = ['-- DEDC eight-table schema and current data. Private files are also required.',
              'SET NAMES utf8mb4;', 'SET FOREIGN_KEY_CHECKS=0;']
    for table in schema.metadata.sorted_tables:
        chunks.append(str(CreateTable(table).compile(dialect=dialect)) + ';')
        chunks.extend(str(CreateIndex(index).compile(dialect=dialect)) + ';' for index in sorted(table.indexes, key=lambda index: index.name))
        # Hex UTF-8 strings and binary values avoid SQL mode and quoting issues.
        for record in connection.execute(select(table)).mappings():
            def literal(value):
                if value is None: return 'NULL'
                if isinstance(value, bool): return '1' if value else '0'
                if isinstance(value, (int, float)): return str(value)
                if isinstance(value, bytes): return "X'" + value.hex() + "'"
                if isinstance(value, datetime): value = value.isoformat(' ')
                return "CONVERT(X'" + str(value).encode('utf-8').hex() + "' USING utf8mb4)"
            columns = ','.join('`' + c.name + '`' for c in table.columns)
            values = ','.join(literal(record[c.name]) for c in table.columns)
            chunks.append(f'INSERT INTO `{table.name}` ({columns}) VALUES ({values});')
    chunks.append('SET FOREIGN_KEY_CHECKS=1;')
    output.write_text('\n\n'.join(chunks) + '\n', encoding='utf-8')
    os.chmod(output, 0o600)


def stage(source, directory, private_root):
    validate_snapshot(source)
    staged_engine = create_engine('sqlite:///' + str(directory / 'eight-tables.db'))
    schema.metadata.create_all(staged_engine)
    files = PrivateFiles(private_root)
    with staged_engine.begin() as c:
        write_state(c, files, source)
    with staged_engine.connect() as c:
        actual = read_state(c, files)
        expected = normalize(source)
        if expected != normalize(actual):
            raise RuntimeError('Lossless round-trip verification failed; source database was not changed.')
        if c.execute(text('PRAGMA foreign_key_check')).all():
            raise RuntimeError('Staged schema contains broken foreign keys.')
        export_sql(c, directory / 'dedc.sql')
        counts = {t.name: c.execute(select(__import__('sqlalchemy').func.count()).select_from(t)).scalar() for t in schema.metadata.sorted_tables}
    print('Verified lossless round trip:', {k: len(v) for k, v in source.items()})
    print('Eight-table row counts:', counts)
    return staged_engine


def activate(staged_engine, source_digest, directory):
    if engine.dialect.name != 'mysql':
        raise RuntimeError('Activation currently supports MySQL only; staging is available for SQLite tests.')
    prefix = 'dedc8_stage_'
    old_prefix = 'dedc8_previous_'
    quote = engine.dialect.identifier_preparer.quote
    with engine.connect() as c:
        if c.execute(text("SELECT GET_LOCK('dedc8:conversion', 30)")).scalar() != 1:
            raise RuntimeError('Another conversion is in progress.')
        c.commit()
        try:
            original_metadata, current = snapshot(c)
            if digest(current) != source_digest:
                raise RuntimeError('Source data changed after staging. Stop writes and run conversion again.')
            existing = set(inspect(c).get_table_names())
            if any(name.startswith((prefix, old_prefix)) for name in existing):
                raise RuntimeError('Staging/previous tables already exist; inspect the earlier conversion before retrying.')
            c.commit()
            # Stage all eight tables before the atomic RENAME. Keep the original
            # tables in place until every record has been copied and checked.
            for table in schema.metadata.sorted_tables:
                ddl = str(CreateTable(table).compile(engine))
                ddl = re.sub(r'((?:CREATE TABLE|REFERENCES)\s+)(`?)(\w+)\2',
                    lambda m: m[1] + quote(prefix + m[3]), ddl)
                c.execute(text(ddl))
                for index in table.indexes:
                    ddl = str(CreateIndex(index).compile(engine))
                    ddl = re.sub(r'(\bON\s+)(`?)' + re.escape(table.name) + r'\2\b',
                                 lambda m: m[1] + quote(prefix + table.name), ddl)
                    c.execute(text(ddl))
            c.commit()
            staged_metadata = MetaData()
            staged_metadata.reflect(c, only=[prefix + t.name for t in schema.metadata.sorted_tables])
            with staged_engine.connect() as source:
                for table in schema.metadata.sorted_tables:
                    records = [dict(r) for r in source.execute(select(table)).mappings()]
                    if records:
                        c.execute(staged_metadata.tables[prefix + table.name].insert(), records)
            c.commit()
            with staged_engine.connect() as source:
                for table in schema.metadata.sorted_tables:
                    expected = sorted([dict(r) for r in source.execute(select(table)).mappings()], key=dumps)
                    actual = sorted([dict(r) for r in c.execute(select(staged_metadata.tables[prefix + table.name])).mappings()], key=dumps)
                    # MySQL reflects TINYINT(1) as integers; SQLite's declared
                    # Boolean returns bool. Python equality correctly treats
                    # 0/False and 1/True as the same SQL value.
                    if expected != actual:
                        raise RuntimeError('Staged MySQL verification failed: ' + table.name)
            # DDL commits in MySQL. Snapshot again immediately before switching.
            _, unchanged = snapshot(c)
            unchanged = {k: v for k, v in unchanged.items() if not k.startswith(prefix)}
            if digest(unchanged) != source_digest:
                raise RuntimeError('Source changed while staging; activation refused.')
            c.commit()
            renames = [f'{quote(name)} TO {quote(old_prefix + name)}' for name in original_metadata.tables]
            renames += [f'{quote(prefix + name)} TO {quote(name)}' for name in schema.metadata.tables]
            c.execute(text('RENAME TABLE ' + ', '.join(renames)))
            c.commit()
            # Validate the active data before discarding old tables. If this
            # fails, both copies remain available for explicit recovery.
            actual = read_state(c, PrivateFiles(settings.PRIVATE_STORAGE_DIR))
            expected = {k: v for k, v in current.items() if k != 'alembic_version'}
            if normalize(actual) != normalize(expected):
                raise RuntimeError('Post-switch verification failed; previous tables retained.')
            for table in reversed(original_metadata.sorted_tables):
                c.execute(text('DROP TABLE ' + quote(old_prefix + table.name)))
            c.commit()
            if set(inspect(c).get_table_names()) != set(schema.metadata.tables):
                raise RuntimeError('Final table inventory is not exactly eight.')
            print('Activated and verified exactly eight MySQL tables. Backup:', directory)
        finally:
            c.rollback()
            c.execute(text("SELECT RELEASE_LOCK('dedc8:conversion')"))
            c.commit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Activate after lossless staging and verification')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    directory = Path('backups').resolve() / ('dedc-eight-tables-' + stamp)
    directory.mkdir(parents=True, mode=0o700)
    with engine.connect() as c:
        metadata, source = snapshot(c)
    with gzip.open(directory / 'source.json.gz', 'wt', encoding='utf-8') as f:
        f.write(dumps(source))
    os.chmod(directory / 'source.json.gz', 0o600)
    (directory / 'source-schema.sql').write_text('\n\n'.join(str(CreateTable(t).compile(engine)) + ';' for t in metadata.sorted_tables))
    os.chmod(directory / 'source-schema.sql', 0o600)
    staged = stage(source, directory, settings.PRIVATE_STORAGE_DIR)
    (directory / 'verification.json').write_text(dumps({'source_sha256': digest(source), 'source_counts': {k: len(v) for k, v in source.items()}, 'private_storage': str(Path(settings.PRIVATE_STORAGE_DIR).resolve()), 'round_trip_verified': True}))
    print('Populated SQL dump:', directory / 'dedc.sql')
    if args.apply:
        activate(staged, digest(source), directory)
    else:
        print('Staging only; source database unchanged. Use --apply to activate after stopping application writes.')
    staged.dispose()

if __name__ == '__main__':
    main()

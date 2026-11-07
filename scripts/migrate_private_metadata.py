"""Back up, dry-run, apply or roll back the private metadata cutover.

Default is read-only for live SQL: backup + isolated staging + lossless verification.
Stop all app/external writers before --apply or --rollback. No schema DDL is run
against the configured DB. Backup files contain private data and are mode 0600.
"""
import argparse
from datetime import date, datetime, timezone
import gzip
import hashlib
import os
from pathlib import Path
import shutil
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.schema import CreateTable, CreateIndex
from app.config import settings
from app.database import engine
from app.storage.codec import PrivateFiles, dumps, loads
from app.storage.compact import CompactSession, projection_snapshot
from app.storage.existing import metadata
from app.storage.journal import digest, snapshot
from app.storage.metadata_migration import plan, migrate, rollback


def write_private(path, content):
    with path.open('wb') as stream:
        os.chmod(path, 0o600)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def files_manifest(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise RuntimeError('Symlink in private backup; inspect it before proceeding.')
        if path.is_file() and path.name != 'workspace.lock':
            result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def sql_dump(connection):
    chunks = ['-- Private DEDC backup: restore into an empty database with the paired private directory.',
              'SET NAMES utf8mb4;', 'SET FOREIGN_KEY_CHECKS=0;']
    dialect = connection.dialect
    for table in metadata.sorted_tables:
        if dialect.name == 'mysql':
            ddl = connection.exec_driver_sql('SHOW CREATE TABLE ' + dialect.identifier_preparer.quote(table.name)).one()[1]
        else:
            ddl = str(CreateTable(table).compile(dialect=dialect))
        chunks.append(ddl + ';')
        if dialect.name != 'mysql':
            chunks.extend(str(CreateIndex(index).compile(dialect=dialect)) + ';' for index in table.indexes)
        for row in connection.execute(select(table)).mappings():
            def literal(value):
                if value is None:
                    return 'NULL'
                if isinstance(value, bool):
                    return '1' if value else '0'
                if isinstance(value, (int, float)):
                    return str(value)
                if isinstance(value, (date, datetime)):
                    value = value.isoformat(' ') if isinstance(value, datetime) else value.isoformat()
                if dialect.name == 'mysql':
                    return "CONVERT(X'" + str(value).encode('utf-8').hex() + "' USING utf8mb4)"
                return "'" + str(value).replace("'", "''") + "'"
            columns = ','.join(dialect.identifier_preparer.quote(c.name) for c in table.c)
            chunks.append(f'INSERT INTO {dialect.identifier_preparer.quote(table.name)} ({columns}) VALUES (' + ','.join(literal(row[c.name]) for c in table.c) + ');')
    chunks.append('SET FOREIGN_KEY_CHECKS=1;')
    return '\n\n'.join(chunks).encode('utf-8')


def verify_backup(directory):
    manifest = loads((directory / 'manifest.json').read_bytes())
    for relative, checksum in manifest.items():
        path = directory / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
            raise RuntimeError('Backup integrity check failed: ' + relative)
    return loads(gzip.decompress((directory / 'database.json.gz').read_bytes()))


def validate_schema(connection):
    inspector = inspect(connection)
    if set(inspector.get_table_names()) != set(metadata.tables):
        raise RuntimeError('Cleanup supports exactly the supplied ten-table schema.')
    for table in metadata.tables.values():
        if {c['name'] for c in inspector.get_columns(table.name)} != set(table.c.keys()):
            raise RuntimeError('Unexpected columns in ' + table.name + '; cleanup refused rather than backing up partial data.')
    if connection.dialect.name == 'mysql':
        if connection.exec_driver_sql("SELECT TRIGGER_NAME FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE() AND EVENT_OBJECT_TABLE='questiontitle'").first():
            raise RuntimeError('questiontitle has SQL triggers; their side effects need separate review before cleanup.')


def dry_run(target, private_root, directory):
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(directory, 0o700)
    with CompactSession(target, private_root, 'maintenance') as db:
        if target.dialect.name == 'mysql':
            db.native.exec_driver_sql('SET TRANSACTION READ ONLY')
        validate_schema(db.native)
        if db.journal:
            raise RuntimeError('Private metadata is already active; no cleanup is necessary.')
        prepared = plan(db.native, db.files)
        source = snapshot(db.native, metadata)
        private = directory / 'private'
        shutil.copytree(db.files.root, private, ignore=shutil.ignore_patterns('workspace.lock'))
        os.chmod(private, 0o700)
        write_private(directory / 'database.json.gz', gzip.compress(dumps(source).encode('utf-8')))
        write_private(directory / 'database.sql', sql_dump(db.native))
        write_private(directory / 'plan.json', dumps(prepared).encode())
        # The exact SQL fingerprint and private-file hashes form the apply precondition.
        private_hashes = files_manifest(private)
        write_private(directory / 'private-hashes.json', dumps(private_hashes).encode())
        manifest = files_manifest(directory)
        write_private(directory / 'manifest.json', dumps(manifest).encode())
        restored = verify_backup(directory)
        if restored != source or files_manifest(private) != private_hashes:
            raise RuntimeError('Backup round-trip verification failed.')
        stage_private = directory / 'staging-private'
        shutil.copytree(private, stage_private)
        stage = create_engine('sqlite:///' + str(directory / 'staging.db'))
        metadata.create_all(stage)  # DDL is confined to this explicitly named staging copy.
        os.chmod(directory / 'staging.db', 0o600)
        with stage.begin() as c:
            for table in metadata.sorted_tables:
                if source[table.name]:
                    c.execute(table.insert(), source[table.name])
        try:
            with CompactSession(stage, stage_private, 'maintenance') as staged:
                before = dumps(projection_snapshot(staged))
                result = migrate(staged.native, staged.files, stage, prepared['before'])
            with CompactSession(stage, stage_private, 'private') as staged:
                if dumps(projection_snapshot(staged)) != before:
                    raise RuntimeError('Isolated migration changed application records.')
                staged.commit()  # A normal no-op request cannot recreate SQL metadata.
                if any(r['description'] and __import__('app.storage.compact', fromlist=['envelope']).envelope(r['description'])
                       for r in staged.native.execute(select(metadata.tables['questiontitle'])).mappings()):
                    raise RuntimeError('Synthetic categories survived staging.')
            with CompactSession(stage, stage_private, 'maintenance') as staged:
                rollback(staged.native, staged.files, stage, prepared, result['after'])
            with CompactSession(stage, stage_private, 'sql') as staged:
                if dumps(projection_snapshot(staged)) != before:
                    raise RuntimeError('Isolated rollback changed application records.')
        finally:
            stage.dispose()
        # Staging uses a second private copy. Verify that the original paired
        # backup stayed byte-identical throughout the rehearsal.
        verify_backup(directory)
        report = {'before': prepared['before'], 'ids': prepared['ids'],
                  'remove_count': len(prepared['ids']), 'keep_categories': len(source['questiontitle']) - len(prepared['ids']),
                  'backup_verified': True, 'isolated_migration_verified': True,
                  'isolated_rollback_verified': True, 'expected_after': result['after'],
                  'logical_counts': {name: len(values) for name, values in loads(before).items()}}
        write_private(directory / 'verification.json', dumps(report).encode())
        manifest['verification.json'] = hashlib.sha256((directory / 'verification.json').read_bytes()).hexdigest()
        write_private(directory / 'manifest.json', dumps(manifest).encode())
        return report


def activate(target, private_root, directory, undo=False):
    verify_backup(directory)
    prepared = loads((directory / 'plan.json').read_bytes())
    verified = loads((directory / 'verification.json').read_bytes())
    with CompactSession(target, private_root, 'maintenance') as db:
        validate_schema(db.native)
        if undo:
            rollback(db.native, db.files, target, prepared, verified['expected_after'])
            return {'rolled_back': True}
        if db.journal:
            return {'already_migrated': True}
        expected_files = loads((directory / 'private-hashes.json').read_bytes())
        if files_manifest(db.files.root) != expected_files:
            raise RuntimeError('Private files changed since backup. Stop writes and repeat the dry run.')
        return migrate(db.native, db.files, target, prepared['before'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--apply', action='store_true')
    action.add_argument('--rollback', action='store_true')
    parser.add_argument('--backup', type=Path)
    args = parser.parse_args()
    if args.apply or args.rollback:
        if args.backup is None:
            parser.error('--apply/--rollback requires the verified --backup directory')
        result = activate(engine, settings.PRIVATE_STORAGE_DIR, args.backup.resolve(), args.rollback)
        print(dumps(result))
        print('Set METADATA_STORAGE=' + ('sql' if args.rollback else 'private') + ' and restart every application worker.')
    else:
        directory = args.backup or Path('backups') / ('metadata-cleanup-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8])
        result = dry_run(engine, settings.PRIVATE_STORAGE_DIR, directory.resolve())
        print('Verified backup:', directory.resolve())
        print(dumps(result))
        print('Live SQL unchanged. Stop all writers and obtain approval before --apply.')


if __name__ == '__main__':
    main()

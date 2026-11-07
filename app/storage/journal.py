"""Recoverable SQL/private-file commits, under the existing workspace locks.

No SQL commit marker is available in the supplied schema. A durable intent
records fingerprints before/after the native transaction. Recovery completes
the file commit only when SQL matches the recorded outcome, and fails closed
on an ambiguous external change. All writers must honor the workspace lock.
"""
import hashlib
import os
from pathlib import Path
import tempfile

from sqlalchemy import select
from app.storage.codec import dumps, loads

FORMAT = 'dedc-private-metadata-v1'


def digest(value):
    return hashlib.sha256(dumps(value).encode('utf-8')).hexdigest()


def snapshot(connection, metadata):
    return {table.name: [dict(row) for row in connection.execute(
        select(table).order_by(*table.primary_key.columns)).mappings()]
        for table in metadata.sorted_tables}


def fingerprint(connection, metadata):
    return digest(snapshot(connection, metadata))


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write(path, value):
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.metadata-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(dumps(value).encode('utf-8'))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class MetadataJournal:
    def __init__(self, files, target, metadata):
        self.files = files
        self.metadata = metadata
        self.database = hashlib.sha256(target.url.render_as_string(hide_password=True).encode()).hexdigest()
        self.current = files.root / 'metadata-current.json'
        self.pending = files.root / 'metadata-pending.json'

    def pointer(self):
        if not self.current.exists():
            return None
        pointer = loads(self.current.read_bytes())
        if pointer.get('format') != FORMAT or pointer.get('database') != self.database:
            raise RuntimeError('Private metadata belongs to a different database or format.')
        # Reading the immutable document validates its hash before use.
        document = loads(self.files.get(pointer['document']))
        if document.get('format') != FORMAT or not isinstance(document.get('payload'), str) or not isinstance(document.get('mappings'), list):
            raise RuntimeError('Invalid private metadata document.')
        return pointer

    def document(self):
        pointer = self.pointer()
        if pointer is None:
            raise RuntimeError('Private metadata is missing. Restore the paired SQL/private backup; do not start an empty workspace.')
        return loads(self.files.get(pointer['document']))

    def prepare(self, before, after, document):
        if self.pending.exists():
            raise RuntimeError('An earlier metadata commit requires recovery before another write.')
        previous = self.pointer()
        next_pointer = None if document is None else {
            'format': FORMAT, 'database': self.database,
            'document': self.files.put(dumps(document).encode('utf-8')),
        }
        intent = {'format': FORMAT, 'database': self.database, 'before': before, 'after': after,
                  'previous': previous, 'next': next_pointer}
        atomic_write(self.pending, {'intent': intent, 'checksum': digest(intent)})

    def recover(self, connection):
        if not self.pending.exists():
            return
        record = loads(self.pending.read_bytes())
        intent = record['intent']
        if record.get('checksum') != digest(intent) or intent.get('format') != FORMAT or intent.get('database') != self.database:
            raise RuntimeError('Metadata journal integrity or database identity check failed.')
        current = self.pointer()
        if current not in (intent['previous'], intent['next']):
            raise RuntimeError('Private metadata changed during an unfinished transaction. Recovery refused.')
        actual = fingerprint(connection, self.metadata)
        if actual == intent['after']:
            if intent['next'] is None:
                self.current.unlink(missing_ok=True)
                sync_directory(self.files.root)
            else:
                # Validate the next document before publishing its pointer.
                loads(self.files.get(intent['next']['document']))
                atomic_write(self.current, intent['next'])
        elif actual == intent['before'] and current == intent['previous']:
            pass  # SQL rolled back: retain the previous metadata revision.
        else:
            raise RuntimeError('SQL differs from both journal outcomes. Stop writes and restore/reconcile the paired backup.')
        self.pending.unlink()
        sync_directory(self.files.root)

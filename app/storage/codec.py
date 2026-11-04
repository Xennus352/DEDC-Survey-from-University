"""Lossless, versioned JSON encoding shared by conversion and runtime storage."""
import base64
from datetime import datetime, date
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import os
import tempfile
import zlib

FORMAT = 'dedc-eight-v1'


def encode(value):
    if isinstance(value, bytes):
        return {'$bytes': base64.b64encode(value).decode('ascii')}
    if isinstance(value, (datetime, date)):
        return {'$type': type(value).__name__, 'value': value.isoformat()}
    if isinstance(value, Decimal):
        return {'$decimal': str(value)}
    raise TypeError(type(value).__name__)


def decode(value):
    if set(value) == {'$bytes'}:
        return base64.b64decode(value['$bytes'], validate=True)
    if set(value) == {'$type', 'value'} and value['$type'] in {'datetime', 'date'}:
        return (datetime if value['$type'] == 'datetime' else date).fromisoformat(value['value'])
    if set(value) == {'$decimal'}:
        return Decimal(value['$decimal'])
    return value


def dumps(value):
    return json.dumps(value, default=encode, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def loads(value):
    return json.loads(value, object_hook=decode)


def pack(value):
    return base64.b64encode(zlib.compress(dumps(value).encode('utf-8'))).decode('ascii')


def unpack(value):
    return loads(zlib.decompress(base64.b64decode(value, validate=True)).decode('utf-8'))


class PrivateFiles:
    """Immutable content-addressed files; SQL commits the references atomically.

    Failed transactions may leave unreferenced files, but never expose partially
    written metadata or revoke a session before its database commit succeeds.
    """
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)

    def put(self, content):
        digest = hashlib.sha256(content).hexdigest()
        path = self.root / digest
        if not path.exists():
            fd, temporary = tempfile.mkstemp(dir=self.root, prefix='.pending-')
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        return digest

    def get(self, digest):
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Invalid private-file reference')
        content = (self.root / digest).read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise RuntimeError('Private-file integrity check failed')
        return content

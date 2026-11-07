"""Explicit, lossless removal of synthetic categories. Caller owns workspace locks."""
import hashlib
from sqlalchemy import select
from app.storage.codec import FORMAT, dumps, loads
from app.storage.compact import envelope, feature_payload, read_state, rows
from app.storage.existing import ExistingLayout, metadata, titles
from app.storage.journal import FORMAT as PRIVATE_FORMAT, MetadataJournal, fingerprint


def state_digest(state):
    # An uninitialized import omits empty feature collections; a private
    # document explicitly represents those collections. Their meaning is equal.
    return hashlib.sha256(dumps({k: v for k, v in state.items() if v != []}).encode()).hexdigest()


def plan(connection, files):
    selected = []
    mappings = []
    keys = set()
    for row in rows(connection, titles):
        meta = envelope(row['description'])
        if not meta:
            continue  # A negative genuine category is not application metadata.
        kind = meta.get('kind')
        if kind == 'question':
            audience, identifier = meta.get('audience'), meta.get('question_id')
            if audience not in {'university', 'ministry'} or not isinstance(identifier, int):
                raise RuntimeError('Invalid question mapping; migration refused.')
            if row['qTDetail'] != f'[DEDC {audience} question {identifier}]':
                raise RuntimeError('Ambiguous category description; migration refused.')
            table = metadata.tables['uniquestion' if audience == 'university' else 'ministryquestion']
            pk = table.c.uQId if audience == 'university' else table.c.mQId
            if connection.execute(select(pk).where(pk == identifier)).first() is None:
                raise RuntimeError('Mapping references a missing native question.')
            for key in ((audience, identifier), (audience, meta.get('key'))):
                if key in keys:
                    raise RuntimeError('Duplicate question mapping; migration refused.')
                keys.add(key)
            mappings.append(meta)
        elif kind == 'metadata':
            if row['qTDetail'] != f"[DEDC form metadata {meta.get('part', -1) + 1}]":
                raise RuntimeError('Ambiguous feature metadata category; migration refused.')
        else:
            raise RuntimeError('Unknown DEDC category envelope; migration refused.')
        selected.append(row)
    identifiers = [row['qTID'] for row in selected]
    for name in ('uniquestion', 'ministryquestion'):
        table = metadata.tables[name]
        if identifiers and connection.execute(select(table.c.qTID).where(table.c.qTID.in_(identifiers))).first():
            raise RuntimeError('A synthetic row is referenced as a genuine category. Resolve the relationship before migration.')
    # This validates fragment completeness/checksums and every private-file reference.
    state = read_state(connection, files, ExistingLayout())
    fragments = [envelope(row['description']) for row in selected
                 if envelope(row['description'])['kind'] == 'metadata']
    if mappings and not fragments:
        raise RuntimeError('Question mappings without feature metadata; migration refused.')
    payload = ''.join(m['data'] for m in sorted(fragments, key=lambda m: m['part'])) if fragments else feature_payload(files, state)
    document = {'format': PRIVATE_FORMAT, 'payload': payload,
                'mappings': sorted(mappings, key=lambda m: (m['audience'], m['question_id']))}
    return {'ids': sorted(identifiers), 'rows': selected, 'document': document,
            'logical_digest': state_digest(state),
            'before': fingerprint(connection, metadata)}


def migrate(connection, files, target, expected=None):
    journal = MetadataJournal(files, target, metadata)
    journal.recover(connection)
    if journal.current.exists():
        if any(envelope(r['description']) for r in rows(connection, titles)):
            raise RuntimeError('Both SQL and private metadata exist. Reconcile before migration.')
        return {'already_migrated': True, 'ids': []}
    prepared = plan(connection, files)
    if expected is not None and prepared['before'] != expected:
        raise RuntimeError('Database changed since the verified backup. Stop writes and repeat the dry run.')
    if prepared['ids']:
        connection.execute(titles.delete().where(titles.c.qTID.in_(prepared['ids'])))
    after = fingerprint(connection, metadata)
    journal.prepare(prepared['before'], after, prepared['document'])
    connection.commit()
    journal.recover(connection)
    actual = read_state(connection, files, ExistingLayout(journal.document()))
    if state_digest(actual) != prepared['logical_digest']:
        raise RuntimeError('Post-migration state mismatch. Stop writes and use the paired backup.')
    connection.commit()
    return {'already_migrated': False, 'ids': prepared['ids'], 'after': after}


def rollback(connection, files, target, saved_plan, expected_after):
    journal = MetadataJournal(files, target, metadata)
    journal.recover(connection)
    actual = fingerprint(connection, metadata)
    if not journal.current.exists():
        if actual == saved_plan['before']:
            return  # Idempotent completed rollback.
        raise RuntimeError('Private metadata missing and SQL does not match the original backup.')
    if journal.document() != saved_plan['document'] or actual not in {saved_plan['before'], expected_after}:
        raise RuntimeError('Workspace changed after migration. Refusing rollback that would discard subsequent work.')
    if actual == expected_after and saved_plan['rows']:
        connection.execute(titles.insert(), saved_plan['rows'])
    restored = fingerprint(connection, metadata)
    if restored != saved_plan['before']:
        raise RuntimeError('Rollback SQL does not match the verified original snapshot.')
    journal.prepare(actual, restored, None)
    connection.commit()
    journal.recover(connection)
    connection.commit()

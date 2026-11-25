"""Explicit candidate v3 entrypoint and atomic additive migration.
Legacy prdc.connect remains available for v2 compatibility; no automatic migration.
"""
import hashlib
import json
import sqlite3
from pathlib import Path
from . import (connect as connect_v2, contract_digest, schema_digest,
               valid_candidate_url, ROOT)
from .hardening import SQL, EXTRA_SQL
from .evidence import DDL

def extension_sql():
    guards=[]
    for table in ('identity_conflict','rights_assertion','lifecycle_event','audit_event'):
        for op in ('UPDATE','DELETE'):
            guards.append(f"CREATE TRIGGER {table}_no_{op.lower()} BEFORE {op} ON {table} BEGIN SELECT RAISE(ABORT,'append only'); END;")
    return DDL+SQL+'\n'.join(guards)+EXTRA_SQL+"""
CREATE TRIGGER legacy_version_state_guard BEFORE UPDATE OF status ON version_detail
 WHEN NEW.status NOT IN ('CANDIDATE','UNKNOWN') OR OLD.status NOT IN ('CANDIDATE','UNKNOWN')
 BEGIN SELECT RAISE(ABORT,'explicit lifecycle reconciliation required'); END;
"""

def digest_v3():
    h=hashlib.sha256()
    for value in (contract_digest().encode(),extension_sql().encode(),
                  (ROOT/'registry/contracts/metadata.json').read_bytes()):
        h.update(len(value).to_bytes(8,'big')); h.update(value)
    return h.hexdigest()

def statements(sql):
    """Execute complete SQL statements without executescript's implicit commit."""
    pending=''
    for line in sql.splitlines(keepends=True):
        pending+=line
        if sqlite3.complete_statement(pending):
            yield pending
            pending=''
    if pending.strip(): raise ValueError('incomplete migration SQL')

def configure(db):
    db.create_function('valid_candidate_url',1,valid_candidate_url,deterministic=True)
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA recursive_triggers=ON')

def legacy_snapshot(db):
    tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name") if r[0]!='schema_info']
    return {t:sorted(db.execute('SELECT * FROM "'+t.replace('"','""')+'"').fetchall(),key=repr) for t in tables}

def validate_v2(db):
    # Compare against independently generated clean schema, not merely stored claims.
    expected=connect_v2()
    try:
        if db.execute('PRAGMA user_version').fetchone()[0]!=2:
            raise ValueError('v2 required')
        if schema_digest(db)!=schema_digest(expected):
            raise ValueError('v2 schema drift')
        if db.execute('SELECT contract_digest,schema_digest FROM schema_info WHERE id=1').fetchone()!=(contract_digest(),schema_digest(expected)):
            raise ValueError('v2 digest mismatch')
        if set(db.execute('SELECT * FROM relation_rule'))!=set(expected.execute('SELECT * FROM relation_rule')):
            raise ValueError('relationship contract mismatch')
        if db.execute('PRAGMA foreign_key_check').fetchone() or db.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]:
            raise ValueError('v2 integrity failure')
        if db.execute("SELECT 1 FROM version_detail WHERE status NOT IN ('CANDIDATE','UNKNOWN') LIMIT 1").fetchone():
            raise ValueError('legacy lifecycle reconciliation required')
    finally: expected.close()

def migrate_connection(db):
    """Caller must supply an idle connection. No nested transactions."""
    if db.in_transaction: raise ValueError('idle connection required')
    configure(db)
    try:
        db.execute('BEGIN IMMEDIATE')
        validate_v2(db)
        before=legacy_snapshot(db)
        for sql in statements(extension_sql()): db.execute(sql)
        # Replace the schema receipt under the transaction, restoring its guard.
        expected_schema=schema_digest(db)
        db.execute('DROP TRIGGER immutable_schema_info_delete')
        db.execute('DELETE FROM schema_info WHERE id=1')
        db.execute('INSERT INTO schema_info VALUES (1,?,?)',(digest_v3(),expected_schema))
        db.execute("CREATE TRIGGER immutable_schema_info_delete BEFORE DELETE ON schema_info BEGIN SELECT RAISE(ABORT,'schema migration required'); END")
        if schema_digest(db)!=expected_schema: raise ValueError('schema guard drift')
        after=legacy_snapshot(db)
        if any(after.get(t)!=rows for t,rows in before.items()):
            raise ValueError('legacy data conservation failure')
        if db.execute('PRAGMA foreign_key_check').fetchone(): raise ValueError('foreign key failure')
        db.execute('PRAGMA user_version=3')
        db.commit()
        return {t:len(rows) for t,rows in before.items()}
    except Exception:
        db.rollback()
        raise

def migrate(path):
    """Explicit migration of existing file; no implicit creation."""
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=rw',uri=True)
    try: return migrate_connection(db)
    finally: db.close()

def expected_schema_v3():
    db=connect_v2()
    try:
        migrate_connection(db)
        return schema_digest(db)
    finally: db.close()

def connect_v3(path=':memory:'):
    """New in-memory candidate or existing explicitly migrated database."""
    if str(path)==':memory:':
        db=connect_v2()
        migrate_connection(db)
        return db
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=rw',uri=True)
    try:
        configure(db)
        expected=expected_schema_v3()
        if db.execute('PRAGMA user_version').fetchone()[0]!=3 or schema_digest(db)!=expected:
            raise ValueError('v3 schema drift or explicit migration required')
        if db.execute('SELECT contract_digest,schema_digest FROM schema_info WHERE id=1').fetchone()!=(digest_v3(),expected):
            raise ValueError('v3 digest mismatch')
        if db.execute('PRAGMA foreign_key_check').fetchone() or db.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]:
            raise ValueError('v3 integrity failure')
        baseline=connect_v2()
        try:
            if set(db.execute('SELECT * FROM relation_rule'))!=set(baseline.execute('SELECT * FROM relation_rule')):
                raise ValueError('relationship contract mismatch')
        finally: baseline.close()
        return db
    except Exception:
        db.close()
        raise

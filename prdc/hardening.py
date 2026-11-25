"""Experimental schema-v3 contracts. Explicit fixture installation only."""
from datetime import datetime
import re
from . import contract, access_contract, valid_candidate_url
from .evidence import DDL, verify_bytes

AUTHORITY = ("institution","organizational_unit","program","source")
ENTITY = AUTHORITY + ("dataset","document","dataset_version","distribution","digital_asset","collection","endpoint","geographic_reference")
SQL = """
CREATE TABLE identity_conflict(
 id INTEGER PRIMARY KEY, authority_id TEXT NOT NULL, namespace TEXT NOT NULL,
 native_id TEXT NOT NULL, proposed_entity TEXT NOT NULL REFERENCES object(id),
 receipt_id TEXT NOT NULL REFERENCES evidence_receipt(id),
 FOREIGN KEY(authority_id,namespace,native_id) REFERENCES native_binding(authority_id,namespace,native_id)
);
CREATE TABLE rights_assertion(
 id INTEGER PRIMARY KEY, distribution_id TEXT NOT NULL REFERENCES object(id),
 receipt_id TEXT NOT NULL REFERENCES evidence_receipt(id),
 access_right TEXT NOT NULL CHECK(access_right IN ('ALLOW','DENY','UNKNOWN')),
 use_right TEXT NOT NULL CHECK(use_right IN ('ALLOW','DENY','UNKNOWN')),
 redistribution_right TEXT NOT NULL CHECK(redistribution_right IN ('ALLOW','DENY','UNKNOWN'))
);
CREATE TABLE lifecycle_event(
 id INTEGER PRIMARY KEY, version_id TEXT NOT NULL REFERENCES version_detail(id),
 old_state TEXT NOT NULL, new_state TEXT NOT NULL,
 receipt_id TEXT NOT NULL REFERENCES evidence_receipt(id)
);
CREATE TABLE audit_event(
 id INTEGER PRIMARY KEY, action TEXT NOT NULL, entity_id TEXT NOT NULL REFERENCES object(id),
 receipt_id TEXT NOT NULL REFERENCES evidence_receipt(id)
);
CREATE TRIGGER receipt_authority_kind BEFORE INSERT ON evidence_receipt
WHEN NOT EXISTS(SELECT 1 FROM object WHERE id=NEW.source_id AND kind IN ('institution','organizational_unit','program','source'))
BEGIN SELECT RAISE(ABORT,'invalid receipt authority'); END;
CREATE TRIGGER binding_types BEFORE INSERT ON native_binding
WHEN NOT EXISTS(SELECT 1 FROM object WHERE id=NEW.authority_id AND kind IN ('institution','organizational_unit','program','source'))
OR NOT EXISTS(SELECT 1 FROM object WHERE id=NEW.entity_id AND kind IN ('institution','organizational_unit','program','source','dataset','document','dataset_version','distribution','digital_asset','collection','endpoint','geographic_reference'))
OR NOT EXISTS(SELECT 1 FROM evidence_receipt WHERE id=NEW.receipt_id AND source_id=NEW.authority_id)
BEGIN SELECT RAISE(ABORT,'invalid native binding'); END;
CREATE TRIGGER conflict_types BEFORE INSERT ON identity_conflict
WHEN NOT EXISTS(SELECT 1 FROM native_binding b JOIN evidence_receipt r ON r.id=NEW.receipt_id AND r.source_id=b.authority_id JOIN object o ON o.id=NEW.proposed_entity WHERE b.authority_id=NEW.authority_id AND b.namespace=NEW.namespace AND b.native_id=NEW.native_id AND b.entity_id<>NEW.proposed_entity AND o.kind IN ('institution','organizational_unit','program','source','dataset','document','dataset_version','distribution','digital_asset','collection','endpoint','geographic_reference'))
BEGIN SELECT RAISE(ABORT,'invalid identity conflict'); END;
CREATE TRIGGER rights_type BEFORE INSERT ON rights_assertion
WHEN NOT EXISTS(SELECT 1 FROM object WHERE id=NEW.distribution_id AND kind='distribution')
BEGIN SELECT RAISE(ABORT,'distribution required'); END;
CREATE TRIGGER lifecycle_transition BEFORE INSERT ON lifecycle_event
WHEN NEW.old_state<>coalesce((SELECT new_state FROM lifecycle_event WHERE version_id=NEW.version_id ORDER BY id DESC LIMIT 1),(SELECT status FROM version_detail WHERE id=NEW.version_id))
OR NOT ((NEW.old_state IN ('CANDIDATE','UNKNOWN') AND NEW.new_state IN ('CURRENT','WITHDRAWN')) OR (NEW.old_state='CURRENT' AND NEW.new_state IN ('SUPERSEDED','WITHDRAWN')) OR (NEW.old_state='SUPERSEDED' AND NEW.new_state='WITHDRAWN'))
OR (NEW.new_state='CURRENT' AND (SELECT count(*) FROM relation WHERE child=NEW.version_id AND role='has_version')<>1)
BEGIN SELECT RAISE(ABORT,'invalid lifecycle transition'); END;
CREATE TRIGGER lifecycle_base_no_update BEFORE UPDATE ON version_detail
WHEN EXISTS(SELECT 1 FROM lifecycle_event WHERE version_id=OLD.id)
BEGIN SELECT RAISE(ABORT,'event-managed version'); END;
CREATE TRIGGER lifecycle_audit AFTER INSERT ON lifecycle_event
BEGIN INSERT INTO audit_event(action,entity_id,receipt_id) VALUES ('VERSION_TRANSITION',NEW.version_id,NEW.receipt_id); END;
CREATE TRIGGER conflict_audit AFTER INSERT ON identity_conflict
BEGIN INSERT INTO audit_event(action,entity_id,receipt_id) VALUES ('IDENTITY_CONFLICT',NEW.proposed_entity,NEW.receipt_id); END;
CREATE TRIGGER rights_audit AFTER INSERT ON rights_assertion
BEGIN INSERT INTO audit_event(action,entity_id,receipt_id) VALUES ('RIGHTS_ASSERTION',NEW.distribution_id,NEW.receipt_id); END;
"""

def install_fixture(db):
    """Not a migration; only a fresh in-memory fixture is supported."""
    if any(row[2] for row in db.execute('PRAGMA database_list')):
        raise ValueError('persistent installation not authorized')
    if db.execute('SELECT count(*) FROM object').fetchone()[0]:
        raise ValueError('fresh fixture required')
    guards = ''
    for table in ('identity_conflict','rights_assertion','lifecycle_event','audit_event'):
        for op in ('UPDATE','DELETE'):
            guards += f"CREATE TRIGGER {table}_no_{op.lower()} BEFORE {op} ON {table} BEGIN SELECT RAISE(ABORT,'append only'); END;\n"
    db.executescript('BEGIN;\n'+DDL+SQL+guards+'COMMIT;')

def require_receipt(db, receipt_id):
    row=db.execute('SELECT digest FROM evidence_receipt WHERE id=?',(receipt_id,)).fetchone()
    if not row or not verify_bytes(db,row[0]):
        raise ValueError('verified artifact required')

def record_conflict(db, authority, namespace, native_id, entity, receipt):
    require_receipt(db,receipt)
    db.execute('INSERT INTO identity_conflict(authority_id,namespace,native_id,proposed_entity,receipt_id) VALUES (?,?,?,?,?)',(authority,namespace,native_id,entity,receipt))

def cardinality_errors(db, entity):
    row=db.execute('SELECT kind FROM object WHERE id=?',(entity,)).fetchone()
    if not row: return ['unknown entity']
    role={'organizational_unit':'contains_unit','program':'contains_unit','dataset_version':'has_version','distribution':'has_distribution'}.get(row[0])
    if role and db.execute('SELECT count(*) FROM relation WHERE child=? AND role=?',(entity,role)).fetchone()[0]!=1:
        return ['exactly one '+role+' parent required']
    return []

def transition(db, version, target, receipt):
    require_receipt(db,receipt)
    if cardinality_errors(db,version): raise ValueError('incomplete version')
    row=db.execute('SELECT status FROM version_detail WHERE id=?',(version,)).fetchone()
    if not row: raise ValueError('unknown version')
    last=db.execute('SELECT new_state FROM lifecycle_event WHERE version_id=? ORDER BY id DESC LIMIT 1',(version,)).fetchone()
    db.execute('INSERT INTO lifecycle_event(version_id,old_state,new_state,receipt_id) VALUES (?,?,?,?)',(version,(last or row)[0],target,receipt))

def record_rights(db, distribution, receipt, access, use, redistribution):
    require_receipt(db,receipt)
    db.execute('INSERT INTO rights_assertion(distribution_id,receipt_id,access_right,use_right,redistribution_right) VALUES (?,?,?,?,?)',(distribution,receipt,access,use,redistribution))

def metadata_errors(record):
    """Bounded structural validation; no semantic or publication qualification."""
    if not isinstance(record,dict): return ['object required']
    fields={x['field']:x for x in contract('metadata.json')}
    errors=[]
    uuid_pattern=r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    enums={'kind':{'dataset','document'},'access_class':{x['code'] for x in access_contract()['classes']},'scope':set(access_contract()['scope']),'rights':{'ALLOW','DENY','UNKNOWN'},'status':{'CANDIDATE','UNKNOWN'}}
    for name in record.keys()-fields.keys(): errors.append('unknown '+str(name))
    for name,field in fields.items():
        value=record.get(name)
        if value is None:
            if field['applicability']=='required': errors.append('missing '+name)
            continue
        typ=field['type']
        ok=False
        if typ=='uuid': ok=isinstance(value,str) and bool(re.fullmatch(uuid_pattern,value))
        elif typ=='string': ok=isinstance(value,str) and bool(value.strip())
        elif typ=='enum': ok=isinstance(value,str) and value in enums.get(name,set())
        elif typ=='array': ok=isinstance(value,list) and bool(value) and all(isinstance(v,str) and (v=='UNKNOWN' or re.fullmatch(uuid_pattern,v)) for v in value)
        elif typ=='object': ok=isinstance(value,dict) and value=={'state':'UNKNOWN'}
        elif typ=='uri': ok=bool(valid_candidate_url(value))
        elif typ=='sha256': ok=isinstance(value,str) and bool(re.fullmatch('[0-9a-f]{64}',value))
        elif typ=='integer': ok=type(value) is int and value>=0
        elif typ=='datetime':
            try: ok=datetime.fromisoformat(value).utcoffset() is not None
            except (ValueError,TypeError): pass
        if not ok: errors.append('invalid '+name)
    if ('checksum' in record)!=('byte_count' in record): errors.append('artifact checksum and count must coexist')
    return errors

"""PRDC candidate foundation. No live acquisition or verified publication."""
import json
import hashlib
import sqlite3
import uuid
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 2

def contract(name):
    return json.loads((ROOT / 'registry' / 'contracts' / name).read_text())

def access_contract():
    return json.loads((ROOT / 'standards/prvds/access.json').read_text())

def sql_values(values):
    return ','.join("'" + x.replace("'", "''") + "'" for x in values)

def ddl():
    kinds = sql_values(x['name'] for x in contract('logical_types.json') if x['kind'] == 'logical_type')
    a = access_contract()
    classes = sql_values(x['code'] for x in a['classes'] if x['code'] != 'PHYSICAL')
    scopes = sql_values(a['scope']); auth = sql_values(a['authorization']); stability = sql_values(a['stability'])
    formats = sql_values(x['code'] for x in contract('formats.json'))
    protocols = sql_values(x['code'] for x in contract('protocols.json'))
    u = contract('institutional_universe.json')
    inst_status = sql_values(u['status']); domains = sql_values(x['code'] for x in u['domains'])
    disp = sql_values(u['member_dispositions']); roles = sql_values(u['roles'])
    return f"""
CREATE TABLE schema_info(id INTEGER PRIMARY KEY CHECK(id=1),contract_digest TEXT NOT NULL,schema_digest TEXT NOT NULL);
CREATE TABLE object(id TEXT PRIMARY KEY NOT NULL CHECK(length(id)=36 AND substr(id,9,1)='-' AND substr(id,14,1)='-' AND substr(id,19,1)='-' AND substr(id,24,1)='-' AND length(replace(id,'-',''))=32 AND replace(id,'-','') NOT GLOB '*[^0-9a-f]*'), kind TEXT NOT NULL CHECK(kind IN ({kinds})), title TEXT NOT NULL CHECK(length(trim(title))>0));
CREATE TRIGGER immutable_identity BEFORE UPDATE OF id,kind ON object BEGIN SELECT RAISE(ABORT,'immutable identity/type'); END;
CREATE TRIGGER no_delete BEFORE DELETE ON object BEGIN SELECT RAISE(ABORT,'retire instead'); END;
CREATE TABLE relation_rule(role TEXT NOT NULL,parent_kind TEXT NOT NULL,child_kind TEXT NOT NULL,max_parents INTEGER,acyclic INTEGER NOT NULL CHECK(acyclic IN (0,1)),PRIMARY KEY(role,parent_kind,child_kind));
CREATE TABLE relation(parent TEXT NOT NULL REFERENCES object(id), child TEXT NOT NULL REFERENCES object(id), role TEXT NOT NULL, PRIMARY KEY(parent,child,role), CHECK(parent<>child));
CREATE TRIGGER typed_relation BEFORE INSERT ON relation BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM relation_rule r JOIN object p ON p.id=NEW.parent JOIN object c ON c.id=NEW.child WHERE r.role=NEW.role AND r.parent_kind=p.kind AND r.child_kind=c.kind) THEN RAISE(ABORT,'invalid relationship types or role') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM relation_rule r JOIN object p ON p.id=NEW.parent JOIN object c ON c.id=NEW.child WHERE r.role=NEW.role AND r.parent_kind=p.kind AND r.child_kind=c.kind AND r.max_parents=1) AND EXISTS(SELECT 1 FROM relation WHERE child=NEW.child AND role=NEW.role) THEN RAISE(ABORT,'multiple canonical parents') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM relation_rule WHERE role=NEW.role AND acyclic=1) AND EXISTS(WITH RECURSIVE descendants(id) AS (SELECT NEW.child UNION SELECT relation.child FROM relation JOIN descendants ON relation.parent=descendants.id WHERE relation.role=NEW.role) SELECT 1 FROM descendants WHERE id=NEW.parent) THEN RAISE(ABORT,'relationship cycle') END;
 SELECT CASE WHEN NEW.role='supersedes' AND NOT EXISTS(SELECT 1 FROM relation p JOIN relation c ON c.parent=p.parent AND c.role='has_version' WHERE p.role='has_version' AND p.child=NEW.parent AND c.child=NEW.child) THEN RAISE(ABORT,'versions require same canonical work') END;
END;
CREATE TRIGGER immutable_relation BEFORE UPDATE ON relation BEGIN SELECT RAISE(ABORT,'replace relation through explicit reconciliation'); END;
CREATE TRIGGER preserve_version_parent BEFORE DELETE ON relation WHEN OLD.role='has_version' AND EXISTS(SELECT 1 FROM relation WHERE role='supersedes' AND (parent=OLD.child OR child=OLD.child)) BEGIN SELECT RAISE(ABORT,'version lineage depends on parent'); END;
CREATE TABLE institution_detail(id TEXT PRIMARY KEY NOT NULL REFERENCES object(id),domain TEXT NOT NULL CHECK(domain IN ({domains})),status TEXT NOT NULL CHECK(status IN ({inst_status})),native_id TEXT,identity_authority TEXT, CHECK(native_id IS NULL OR length(trim(native_id))>0), CHECK((native_id IS NULL)=(identity_authority IS NULL)), CHECK(identity_authority IS NULL OR length(trim(identity_authority))>0), UNIQUE(identity_authority,native_id));
CREATE TABLE institution_role(id TEXT NOT NULL REFERENCES institution_detail(id),role TEXT NOT NULL CHECK(role IN ({roles})),PRIMARY KEY(id,role));
CREATE TABLE institution_alias(id TEXT NOT NULL REFERENCES institution_detail(id),alias TEXT NOT NULL CHECK(length(trim(alias))>0),PRIMARY KEY(id,alias));
CREATE TABLE universe(id TEXT PRIMARY KEY NOT NULL REFERENCES object(id),mode TEXT NOT NULL CHECK(mode IN ('CLOSED','OPEN')),scope TEXT NOT NULL CHECK(length(trim(scope))>0));
CREATE TABLE universe_snapshot(id TEXT PRIMARY KEY NOT NULL REFERENCES object(id),universe_id TEXT NOT NULL REFERENCES universe(id),source_receipt TEXT REFERENCES object(id),reported_count INTEGER CHECK(reported_count IS NULL OR (typeof(reported_count)='integer' AND reported_count>=0)),observed_at TEXT NOT NULL CHECK(length(trim(observed_at))>0));
CREATE TABLE universe_member(snapshot_id TEXT NOT NULL REFERENCES universe_snapshot(id),member_id TEXT NOT NULL REFERENCES institution_detail(id),disposition TEXT NOT NULL CHECK(disposition IN ({disp})),PRIMARY KEY(snapshot_id,member_id));
CREATE TABLE version_detail(id TEXT PRIMARY KEY NOT NULL REFERENCES object(id),native_version TEXT, status TEXT NOT NULL CHECK(status IN ('CANDIDATE','CURRENT','SUPERSEDED','WITHDRAWN','UNKNOWN')));
CREATE TABLE access(id TEXT PRIMARY KEY NOT NULL REFERENCES object(id),url TEXT NOT NULL CHECK(valid_candidate_url(url)=1),class TEXT NOT NULL CHECK(class IN ({classes})),scope TEXT NOT NULL CHECK(scope IN ({scopes})),status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status='PENDING'),authorization TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK(authorization IN ({auth})),stability TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK(stability IN ({stability})),protocol TEXT NOT NULL DEFAULT 'HTTP_S3' CHECK(protocol IN ({protocols})),format TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK(format IN ({formats})));
CREATE INDEX relation_child_role ON relation(child,role);
CREATE INDEX relation_parent_role ON relation(parent,role);
CREATE INDEX universe_member_member ON universe_member(member_id);
"""

def type_guards(db):
    for table, col, kinds in [
        ('institution_detail','id',['institution','organizational_unit','program']),
        ('universe','id',['institutional_universe']),
        ('universe_snapshot','id',['denominator']),
        ('universe_snapshot','source_receipt',['source_receipt']),
        ('version_detail','id',['dataset_version']),
        ('access','id',['endpoint']),
    ]:
        allowed = sql_values(kinds)
        for op in ('INSERT','UPDATE'):
            db.execute(f"""CREATE TRIGGER {table}_{col}_{op.lower()} BEFORE {op} ON {table} WHEN NEW.{col} IS NOT NULL AND NOT EXISTS(SELECT 1 FROM object WHERE id=NEW.{col} AND kind IN ({allowed})) BEGIN SELECT RAISE(ABORT,'invalid specialized identity'); END""")
    for op in ('UPDATE','DELETE'):
        db.execute(f"CREATE TRIGGER immutable_schema_info_{op.lower()} BEFORE {op} ON schema_info BEGIN SELECT RAISE(ABORT,'schema migration required'); END")
    for op in ('INSERT','UPDATE','DELETE'):
        db.execute(f"CREATE TRIGGER immutable_rule_{op.lower()} BEFORE {op} ON relation_rule BEGIN SELECT RAISE(ABORT,'contract migration required'); END")

def contract_digest():
    h=hashlib.sha256()
    for name in ('logical_types.json','relationship_rules.json','formats.json','protocols.json','institutional_universe.json'):
        h.update(name.encode()); h.update((ROOT/'registry/contracts'/name).read_bytes())
    h.update((ROOT/'standards/prvds/access.json').read_bytes()); h.update(ddl().encode())
    return h.hexdigest()

def schema_digest(db):
    rows=db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()

def connect(path=':memory:'):
    db = sqlite3.connect(path)
    db.create_function('valid_candidate_url',1,valid_candidate_url,deterministic=True)
    db.execute('PRAGMA foreign_keys=ON')
    version = db.execute('PRAGMA user_version').fetchone()[0]
    existing = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
    try:
        if version == 0 and not existing:
            # DDL and vocabulary initialization in one transaction.
            db.executescript('BEGIN;\n' + ddl())
            db.executemany('INSERT INTO relation_rule VALUES (?,?,?,?,?)',[(r['role'],r['parent_kind'],r['child_kind'],r['max_parents'],int(r['acyclic'])) for r in contract('relationship_rules.json')])
            type_guards(db)
            db.execute('INSERT INTO schema_info VALUES (1,?,?)',(contract_digest(),schema_digest(db)))
            db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
            db.commit()
        elif version != SCHEMA_VERSION:
            raise ValueError('unsupported schema; explicit verified migration required')
        else:
            # A matching version alone is not proof of a matching database contract.
            if db.execute('SELECT contract_digest,schema_digest FROM schema_info WHERE id=1').fetchone() != (contract_digest(),schema_digest(db)):
                raise ValueError('schema or contract drift')
            expected = {(r['role'],r['parent_kind'],r['child_kind'],r['max_parents'],int(r['acyclic'])) for r in contract('relationship_rules.json')}
            if set(db.execute('SELECT * FROM relation_rule')) != expected:
                raise ValueError('relationship contract mismatch')
            if db.execute('PRAGMA foreign_key_check').fetchone():
                raise ValueError('foreign key integrity failure')
        return db
    except Exception:
        db.rollback(); db.close(); raise

def create(db, kind, title):
    key = str(uuid.uuid4())
    db.execute('INSERT INTO object VALUES (?,?,?)',(key,kind,title))
    return key

def valid_candidate_url(url):
    if not isinstance(url,str) or any(ord(c)<32 or ord(c)==127 or c.isspace() for c in url): return 0
    try:
        u=urlsplit(url)
        port=u.port
        if u.scheme not in ('http','https') or not u.hostname or u.username is not None or u.password is not None or u.fragment or '\\' in url: return 0
        sensitive={'token','access_token','api_key','apikey','key','signature','sig','password','credential','x-amz-signature','x-amz-credential','x-amz-security-token'}
        if any(k.lower() in sensitive for k,v in parse_qsl(u.query,keep_blank_values=True)): return 0
    except (ValueError,UnicodeError): return 0
    return 1

def candidate_link(db,key,url,access_class,scope,*,authorization='UNKNOWN',stability='UNKNOWN',protocol='HTTP_S3',format_code='UNKNOWN'):
    if not valid_candidate_url(url): raise ValueError('invalid candidate URL or possible credential')
    db.execute('INSERT INTO access(id,url,class,scope,status,authorization,stability,protocol,format) VALUES (?,?,?,?,?,?,?,?,?)',(key,url,access_class,scope,'PENDING',authorization,stability,protocol,format_code))

def eligible_for_verified_publication(record):
    # Verified publication deliberately disabled pending evidence/rights/security qualification.
    return False

def ratio(n,d):
    if not isinstance(n,int) or isinstance(n,bool) or (d is not None and (not isinstance(d,int) or isinstance(d,bool))) or n<0 or (d is not None and (d<0 or n>d)): raise ValueError('invalid counts')
    return None if not d else n/d

def universe_coverage(db,snapshot_id):
    row=db.execute('SELECT s.reported_count,s.source_receipt,u.mode FROM universe_snapshot s JOIN universe u ON u.id=s.universe_id WHERE s.id=?',(snapshot_id,)).fetchone()
    if row is None: raise ValueError('unknown snapshot')
    total,receipt,mode=row
    retrieved,classified=db.execute("SELECT count(*),coalesce(sum(disposition IN ('IN_SCOPE','EXCLUDED')),0) FROM universe_member WHERE snapshot_id=?",(snapshot_id,)).fetchone()
    # Structural counts only: receipt identity is not proof of valid source bytes.
    measurable=mode=='CLOSED' and receipt is not None and total is not None and total>0 and retrieved<=total
    state='CONFLICTING' if total is not None and retrieved>total else ('COUNT_MATCH_ONLY' if measurable and retrieved==total else ('PARTIAL' if measurable else 'NOT_MEASURABLE'))
    return {'reported':total,'retrieved':retrieved,'classified':classified,'reconciliation':ratio(retrieved,total) if measurable else None,'classification':ratio(classified,retrieved),'state':state,'certified':False}

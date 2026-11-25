"""Candidate evidence and native identity contracts; no publication authority."""
import hashlib
import sqlite3
from datetime import datetime, timezone

DDL = """
CREATE TABLE IF NOT EXISTS evidence_bytes(
 digest TEXT PRIMARY KEY NOT NULL CHECK(length(digest)=64 AND digest NOT GLOB '*[^0-9a-f]*'),
 content BLOB NOT NULL CHECK(typeof(content)='blob'),
 byte_count INTEGER NOT NULL CHECK(typeof(byte_count)='integer' AND byte_count=length(content))
);
CREATE TABLE IF NOT EXISTS evidence_receipt(
 id TEXT PRIMARY KEY NOT NULL REFERENCES object(id),
 digest TEXT NOT NULL REFERENCES evidence_bytes(digest),
 source_id TEXT NOT NULL REFERENCES object(id),
 observed_at TEXT NOT NULL CHECK(length(trim(observed_at))>0)
);
CREATE TABLE IF NOT EXISTS native_binding(
 authority_id TEXT NOT NULL REFERENCES object(id),
 namespace TEXT NOT NULL CHECK(length(trim(namespace))>0),
 native_id TEXT NOT NULL CHECK(length(trim(native_id))>0),
 entity_id TEXT NOT NULL REFERENCES object(id),
 receipt_id TEXT NOT NULL REFERENCES evidence_receipt(id),
 PRIMARY KEY(authority_id,namespace,native_id)
);
CREATE TRIGGER IF NOT EXISTS evidence_receipt_kind BEFORE INSERT ON evidence_receipt
WHEN NOT EXISTS(SELECT 1 FROM object WHERE id=NEW.id AND kind='source_receipt')
BEGIN SELECT RAISE(ABORT,'receipt identity required'); END;
CREATE TRIGGER IF NOT EXISTS evidence_receipt_no_update BEFORE UPDATE ON evidence_receipt
BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
CREATE TRIGGER IF NOT EXISTS evidence_receipt_no_delete BEFORE DELETE ON evidence_receipt
BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
CREATE TRIGGER IF NOT EXISTS evidence_bytes_no_update BEFORE UPDATE ON evidence_bytes
BEGIN SELECT RAISE(ABORT,'immutable bytes'); END;
CREATE TRIGGER IF NOT EXISTS evidence_bytes_no_delete BEFORE DELETE ON evidence_bytes
BEGIN SELECT RAISE(ABORT,'immutable bytes'); END;
CREATE TRIGGER IF NOT EXISTS native_binding_no_update BEFORE UPDATE ON native_binding
BEGIN SELECT RAISE(ABORT,'immutable identity assertion'); END;
CREATE TRIGGER IF NOT EXISTS native_binding_no_delete BEFORE DELETE ON native_binding
BEGIN SELECT RAISE(ABORT,'immutable identity assertion'); END;
"""

def record_bytes(db, content):
    if not isinstance(content, bytes):
        raise TypeError('bytes required')
    digest = hashlib.sha256(content).hexdigest()
    db.execute('INSERT OR IGNORE INTO evidence_bytes VALUES (?,?,?)',
               (digest, content, len(content)))
    if not verify_bytes(db, digest):
        raise ValueError('artifact integrity failure')
    return digest

def verify_bytes(db, digest):
    row = db.execute('SELECT content,byte_count FROM evidence_bytes WHERE digest=?',
                     (digest,)).fetchone()
    return bool(row and isinstance(row[0], bytes) and len(row[0]) == row[1]
                and hashlib.sha256(row[0]).hexdigest() == digest)

def record_receipt(db, receipt_id, source_id, content, observed_at):
    timestamp = datetime.fromisoformat(observed_at)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError('offset-aware observation required')
    digest = record_bytes(db, content)
    db.execute('INSERT INTO evidence_receipt VALUES (?,?,?,?)',
               (receipt_id, digest, source_id, timestamp.astimezone(timezone.utc).isoformat()))
    return digest

def bind_native(db, authority_id, namespace, native_id, entity_id, receipt_id):
    row = db.execute('SELECT digest FROM evidence_receipt WHERE id=? AND source_id=?',
                     (receipt_id, authority_id)).fetchone()
    if not row or not verify_bytes(db, row[0]):
        raise ValueError('matching authority receipt and verified bytes required')
    if not all(isinstance(v,str) and v.strip() and v==v.strip() for v in (namespace,native_id)):
        raise ValueError('nonempty exact native identifier required')
    db.execute('INSERT INTO native_binding VALUES (?,?,?,?,?)',
               (authority_id,namespace,native_id,entity_id,receipt_id))

PRAGMA foreign_keys=ON;
CREATE TABLE resource(id TEXT PRIMARY KEY,kind TEXT NOT NULL CHECK(kind IN ('dataset','series','document','software','model','imagery','audio','video','stream','service','composite','opaque')),title TEXT NOT NULL,classification TEXT NOT NULL CHECK(classification IN ('CANDIDATE','UNCLASSIFIED','CONFLICTING')),status TEXT NOT NULL CHECK(status IN ('DRAFT','QUARANTINED')));
CREATE TABLE subject(id TEXT PRIMARY KEY);
CREATE TABLE resource_subject(resource_id TEXT NOT NULL REFERENCES resource(id),subject_id TEXT NOT NULL REFERENCES subject(id),PRIMARY KEY(resource_id,subject_id));
CREATE TABLE source_binding(id TEXT PRIMARY KEY,resource_id TEXT NOT NULL REFERENCES resource(id),authority_namespace TEXT NOT NULL,native_type TEXT NOT NULL,native_id TEXT NOT NULL,scope TEXT NOT NULL,UNIQUE(authority_namespace,native_type,native_id,scope));
CREATE TABLE receipt(id TEXT PRIMARY KEY,source_ref TEXT NOT NULL REFERENCES source_binding(id),acquired_at TEXT NOT NULL,sha256 TEXT NOT NULL CHECK(length(sha256)=64 AND sha256 NOT GLOB '*[^0-9a-f]*'),byte_count INTEGER NOT NULL CHECK(byte_count>=0),artifact_ref TEXT NOT NULL);
CREATE TABLE version(id TEXT PRIMARY KEY,resource_id TEXT NOT NULL REFERENCES resource(id),label TEXT NOT NULL,previous_version_id TEXT,receipt_id TEXT NOT NULL REFERENCES receipt(id),state TEXT NOT NULL CHECK(state IN ('CANDIDATE','SUPERSEDED','WITHDRAWN')),UNIQUE(resource_id,id),UNIQUE(resource_id,label),CHECK(previous_version_id IS NULL OR previous_version_id<>id),FOREIGN KEY(resource_id,previous_version_id) REFERENCES version(resource_id,id));
CREATE TABLE geography(id TEXT PRIMARY KEY,applicability TEXT NOT NULL CHECK(applicability IN ('DIRECT','INTERSECTING','CONTEXTUAL','GLOBAL','NONSPATIAL','UNKNOWN')),geometry_ref TEXT,crs TEXT,authority_ref TEXT,evidence_ref TEXT REFERENCES receipt(id));
CREATE TABLE temporal(id TEXT PRIMARY KEY,axis TEXT NOT NULL CHECK(axis IN ('OBSERVATION','VALID','PUBLICATION','ACQUISITION','REVISION','FORECAST','FISCAL')),start TEXT,end TEXT,precision TEXT NOT NULL CHECK(precision IN ('INSTANT','DAY','MONTH','YEAR','INTERVAL','UNKNOWN')));
CREATE TABLE rights(id TEXT PRIMARY KEY,access TEXT NOT NULL CHECK(access IN ('PUBLIC','AUTHENTICATED','RESTRICTED','COMMERCIAL','UNKNOWN')),redistribution TEXT NOT NULL CHECK(redistribution IN ('PERMITTED','PROHIBITED','CONDITIONAL','UNKNOWN')),license_id TEXT,evidence_ref TEXT REFERENCES receipt(id));
CREATE TRIGGER receipt_no_update BEFORE UPDATE ON receipt BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
CREATE TRIGGER receipt_no_delete BEFORE DELETE ON receipt BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
CREATE TRIGGER version_no_update BEFORE UPDATE ON version BEGIN SELECT RAISE(ABORT,'immutable version; successor required'); END;
CREATE TRIGGER version_no_delete BEFORE DELETE ON version BEGIN SELECT RAISE(ABORT,'immutable version'); END;

-- Bounded lifecycle and ownership extension. Existing historical records are untouched.
CREATE TRIGGER version_receipt_owner BEFORE INSERT ON version
WHEN NOT EXISTS (SELECT 1 FROM receipt r JOIN source_binding s ON s.id=r.source_ref WHERE r.id=NEW.receipt_id AND s.resource_id=NEW.resource_id)
BEGIN SELECT RAISE(ABORT,'receipt belongs to another resource'); END;
CREATE TRIGGER source_binding_no_update BEFORE UPDATE ON source_binding BEGIN SELECT RAISE(ABORT,'immutable source binding'); END;
CREATE TRIGGER source_binding_no_delete BEFORE DELETE ON source_binding BEGIN SELECT RAISE(ABORT,'immutable source binding'); END;
CREATE TABLE version_event(
 id TEXT PRIMARY KEY NOT NULL, version_id TEXT NOT NULL REFERENCES version(id),
 seq INTEGER NOT NULL CHECK(typeof(seq)='integer' AND seq>0),
 state TEXT NOT NULL CHECK(state IN ('QUALIFIED','SUPERSEDED','WITHDRAWN')),
 receipt_id TEXT NOT NULL REFERENCES receipt(id), UNIQUE(version_id,seq)
);
CREATE TRIGGER version_event_admission BEFORE INSERT ON version_event BEGIN
 SELECT CASE WHEN NEW.seq != COALESCE((SELECT MAX(seq) FROM version_event WHERE version_id=NEW.version_id),0)+1 THEN RAISE(ABORT,'event sequence') END;
 SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM version v JOIN receipt r ON r.id=NEW.receipt_id JOIN source_binding s ON s.id=r.source_ref WHERE v.id=NEW.version_id AND v.resource_id=s.resource_id) THEN RAISE(ABORT,'event evidence owner') END;
 SELECT CASE WHEN NOT (
 (COALESCE((SELECT state FROM version_event WHERE version_id=NEW.version_id ORDER BY seq DESC LIMIT 1),(SELECT state FROM version WHERE id=NEW.version_id))='CANDIDATE' AND NEW.state IN ('QUALIFIED','WITHDRAWN')) OR
 (COALESCE((SELECT state FROM version_event WHERE version_id=NEW.version_id ORDER BY seq DESC LIMIT 1),(SELECT state FROM version WHERE id=NEW.version_id))='QUALIFIED' AND NEW.state IN ('SUPERSEDED','WITHDRAWN'))
 ) THEN RAISE(ABORT,'invalid lifecycle transition') END;
END;
CREATE TRIGGER version_event_no_update BEFORE UPDATE ON version_event BEGIN SELECT RAISE(ABORT,'immutable lifecycle event'); END;
CREATE TRIGGER version_event_no_delete BEFORE DELETE ON version_event BEGIN SELECT RAISE(ABORT,'immutable lifecycle event'); END;
CREATE VIEW version_current_state AS SELECT v.id, COALESCE((SELECT e.state FROM version_event e WHERE e.version_id=v.id ORDER BY e.seq DESC LIMIT 1),v.state) AS state FROM version v;
CREATE TABLE resource_rights(resource_id TEXT NOT NULL REFERENCES resource(id),rights_id TEXT NOT NULL REFERENCES rights(id),PRIMARY KEY(resource_id,rights_id));
CREATE TRIGGER rights_binding_admission BEFORE INSERT ON resource_rights BEGIN
 SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM rights x WHERE x.id=NEW.rights_id AND (x.redistribution='UNKNOWN' OR (x.license_id IS NOT NULL AND x.evidence_ref IS NOT NULL)) AND (x.evidence_ref IS NULL OR EXISTS (SELECT 1 FROM receipt r JOIN source_binding s ON s.id=r.source_ref WHERE r.id=x.evidence_ref AND s.resource_id=NEW.resource_id))) THEN RAISE(ABORT,'rights evidence missing or foreign') END;
END;
CREATE TRIGGER rights_no_update BEFORE UPDATE ON rights BEGIN SELECT RAISE(ABORT,'immutable rights assertion'); END;
CREATE TRIGGER rights_no_delete BEFORE DELETE ON rights BEGIN SELECT RAISE(ABORT,'immutable rights assertion'); END;

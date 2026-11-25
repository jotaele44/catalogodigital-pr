import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from prdc import connect, create, candidate_link, schema_digest
from prdc.schema_v3 import migrate, connect_v3, legacy_snapshot, migrate_connection
from prdc.evidence import record_receipt

class MigrationTests(unittest.TestCase):
    def fixture(self,path):
        db=connect(path)
        source=create(db,'source','Synthetic source')
        work=create(db,'dataset','Synthetic dataset')
        version=create(db,'dataset_version','Synthetic version')
        endpoint=create(db,'endpoint','Synthetic endpoint')
        db.execute("INSERT INTO relation VALUES (?,?,'source_asset')",(source,work))
        db.execute("INSERT INTO relation VALUES (?,?,'has_version')",(work,version))
        db.execute("INSERT INTO version_detail VALUES (?,'1','CANDIDATE')",(version,))
        candidate_link(db,endpoint,'https://example.org/data.csv','FILE','COMPLETE_FILE')
        db.commit()
        return db,source
    def test_fresh_v3(self):
        db=connect_v3()
        self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],3)
        a=create(db,'source','Fixture source')
        r=create(db,'source_receipt','Fixture receipt')
        record_receipt(db,r,a,b'bytes','2026-01-01T00:00:00Z')
        db.close()
    def test_conservation_and_reopen(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'v2.db'
            db,_=self.fixture(p)
            before=legacy_snapshot(db)
            db.close()
            counts=migrate(p)
            self.assertEqual(counts,{t:len(rows) for t,rows in before.items()})
            db=connect_v3(p)
            after=legacy_snapshot(db)
            self.assertEqual(before,{t:after[t] for t in before})
            db.close()
            with self.assertRaises(ValueError): connect(p)
    def test_rollback_after_ddl(self):
        db=connect()
        create(db,'dataset','Preserve')
        db.commit()
        before=legacy_snapshot(db)
        old_schema=schema_digest(db)
        with patch('prdc.schema_v3.digest_v3',side_effect=RuntimeError('injected failure')):
            with self.assertRaises(RuntimeError): migrate_connection(db)
        self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],2)
        self.assertEqual(schema_digest(db),old_schema)
        self.assertEqual(legacy_snapshot(db),before)
        db.close()
    def test_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'v2.db'
            db,_=self.fixture(p)
            db.execute('DROP TRIGGER immutable_identity')
            db.commit(); db.close()
            with self.assertRaisesRegex(ValueError,'drift'): migrate(p)
    def test_v3_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'v2.db'
            db,_=self.fixture(p); db.close(); migrate(p)
            db=sqlite3.connect(p); db.execute('DROP TRIGGER binding_types'); db.commit(); db.close()
            with self.assertRaisesRegex(ValueError,'drift'): connect_v3(p)
    def test_legacy_current_blocked(self):
        db=connect()
        v=create(db,'dataset_version','Legacy')
        db.execute("INSERT INTO version_detail VALUES (?,'1','CURRENT')",(v,))
        db.commit()
        with self.assertRaisesRegex(ValueError,'lifecycle'): migrate_connection(db)
        self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],2)
        db.close()
    def test_no_implicit_migration(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'v2.db'
            db,_=self.fixture(p); db.close()
            with self.assertRaises(ValueError): connect_v3(p)

import unittest
import sqlite3
from prdc import connect, create
from prdc.evidence import record_receipt, bind_native
from prdc.hardening import install_fixture, record_conflict, cardinality_errors, transition, record_rights, metadata_errors

class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.db=connect()
        install_fixture(self.db)
        self.auth=create(self.db,'institution','Synthetic authority')
        self.receipt=create(self.db,'source_receipt','Synthetic receipt')
        record_receipt(self.db,self.receipt,self.auth,b'fixture','2026-01-01T00:00:00Z')
    def tearDown(self): self.db.close()
    def test_receipt_type(self):
        bad=create(self.db,'subject','Not authority')
        rec=create(self.db,'source_receipt','Another receipt')
        with self.assertRaises(sqlite3.IntegrityError):
            record_receipt(self.db,rec,bad,b'x','2026-01-01T00:00:00Z')
    def test_binding_type(self):
        bad=create(self.db,'subject','Not entity')
        with self.assertRaises(sqlite3.IntegrityError):
            bind_native(self.db,self.auth,'fixture','1',bad,self.receipt)
    def test_conflict(self):
        other=create(self.db,'institution','Other')
        bind_native(self.db,self.auth,'fixture','1',self.auth,self.receipt)
        record_conflict(self.db,self.auth,'fixture','1',other,self.receipt)
        self.assertEqual(self.db.execute('SELECT entity_id FROM native_binding').fetchone()[0],self.auth)
        self.assertEqual(self.db.execute('SELECT count(*) FROM audit_event').fetchone()[0],1)
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute('DELETE FROM identity_conflict')
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute('DELETE FROM audit_event')
    def test_cardinality(self):
        v=create(self.db,'dataset_version','Version')
        self.assertTrue(cardinality_errors(self.db,v))
        d=create(self.db,'dataset','Dataset')
        self.db.execute("INSERT INTO relation VALUES (?,?,'has_version')",(d,v))
        self.assertFalse(cardinality_errors(self.db,v))
    def test_lifecycle(self):
        d=create(self.db,'dataset','Dataset')
        v=create(self.db,'dataset_version','Version')
        self.db.execute("INSERT INTO relation VALUES (?,?,'has_version')",(d,v))
        self.db.execute("INSERT INTO version_detail VALUES (?,'1','CANDIDATE')",(v,))
        transition(self.db,v,'CURRENT',self.receipt)
        transition(self.db,v,'SUPERSEDED',self.receipt)
        with self.assertRaises(sqlite3.IntegrityError): transition(self.db,v,'CURRENT',self.receipt)
    def test_rights(self):
        d=create(self.db,'distribution','Distribution')
        record_rights(self.db,d,self.receipt,'ALLOW','UNKNOWN','DENY')
        self.assertEqual(self.db.execute('SELECT redistribution_right FROM rights_assertion').fetchone()[0],'DENY')
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute("UPDATE rights_assertion SET redistribution_right='ALLOW'")
    def test_metadata(self):
        r=dict(asset_id=self.auth,title='Fixture',kind='dataset',source_ref=self.auth,geography=['UNKNOWN'],temporal_coverage={'state':'UNKNOWN'},subjects=[self.auth],access_class='FILE',scope='COMPLETE_FILE',rights='UNKNOWN',status='CANDIDATE')
        self.assertEqual(metadata_errors(r),[])
        r.update(byte_count=True,status='VERIFIED')
        self.assertTrue(metadata_errors(r))

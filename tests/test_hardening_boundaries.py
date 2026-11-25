import unittest
import sqlite3
from prdc import connect, create
from prdc.evidence import record_receipt
from prdc.hardening import install_fixture, transition, record_rights, effective_rights, valid_temporal

class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.db=connect()
        install_fixture(self.db)
        a=create(self.db,'institution','Fixture authority')
        self.r=create(self.db,'source_receipt','Fixture receipt')
        record_receipt(self.db,self.r,a,b'fixture','2026-01-01T00:00:00Z')
    def tearDown(self): self.db.close()
    def version(self,d):
        v=create(self.db,'dataset_version','Version')
        self.db.execute("INSERT INTO version_detail VALUES (?,'1','CANDIDATE')",(v,))
        self.db.execute("INSERT INTO relation VALUES (?,?,'has_version')",(d,v))
        return v
    def test_current_unique(self):
        d=create(self.db,'dataset','Work')
        a,b=self.version(d),self.version(d)
        transition(self.db,a,'CURRENT',self.r)
        with self.assertRaises(sqlite3.IntegrityError): transition(self.db,b,'CURRENT',self.r)
        transition(self.db,a,'SUPERSEDED',self.r)
        transition(self.db,b,'CURRENT',self.r)
    def test_parent_protected(self):
        d=create(self.db,'dataset','Work')
        v=self.version(d)
        transition(self.db,v,'CURRENT',self.r)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM relation WHERE child=?",(v,))
    def test_replace_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT OR REPLACE INTO evidence_receipt SELECT * FROM evidence_receipt")
    def test_rights_intersection(self):
        d=create(self.db,'distribution','Distribution')
        self.assertEqual(effective_rights(self.db,d)['access'],'UNKNOWN')
        record_rights(self.db,d,self.r,'ALLOW','UNKNOWN','ALLOW')
        record_rights(self.db,d,self.r,'DENY','ALLOW','UNKNOWN')
        self.assertEqual(effective_rights(self.db,d),{'access':'DENY','use':'UNKNOWN','redistribution':'UNKNOWN'})
    def test_temporal(self):
        self.assertTrue(valid_temporal({'start':'2026-01-01T00:00:00Z','end':'2026-01-02T00:00:00Z'}))
        self.assertFalse(valid_temporal({'start':'2026-01-02T00:00:00Z','end':'2026-01-01T00:00:00Z'}))
        self.assertFalse(valid_temporal({'start':'2026-01-01','end':'2026-01-02'}))

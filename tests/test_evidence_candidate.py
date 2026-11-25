import unittest
import sqlite3
from prdc import connect, create
from prdc.evidence import DDL, record_receipt, verify_bytes, bind_native

class EvidenceCandidateTests(unittest.TestCase):
    def setUp(self):
        self.db=connect()
        # Isolated experimental schema only; no production migration.
        self.db.executescript(DDL)
        self.authority=create(self.db,'institution','Synthetic authority')
        self.entity=create(self.db,'institution','Synthetic entity')
        self.receipt=create(self.db,'source_receipt','Synthetic receipt')
        self.digest=record_receipt(self.db,self.receipt,self.authority,b'fixture','2026-01-01T00:00:00Z')
    def tearDown(self):
        self.db.close()
    def test_digest(self):
        self.assertTrue(verify_bytes(self.db,self.digest))
        self.assertFalse(verify_bytes(self.db,'0'*64))
    def test_receipt_immutable(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute('DELETE FROM evidence_receipt WHERE id=?',(self.receipt,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute('UPDATE evidence_receipt SET observed_at=? WHERE id=?',('changed',self.receipt))
    def test_bytes_immutable(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute('UPDATE evidence_bytes SET content=? WHERE digest=?',(b'forged!',self.digest))
    def test_binding(self):
        bind_native(self.db,self.authority,'fixture','123',self.entity,self.receipt)
        with self.assertRaises(sqlite3.IntegrityError):
            bind_native(self.db,self.authority,'fixture','123',self.authority,self.receipt)
    def test_wrong_authority(self):
        with self.assertRaises(ValueError):
            bind_native(self.db,self.entity,'fixture','123',self.authority,self.receipt)
    def test_naive_timestamp(self):
        with self.assertRaises(ValueError):
            record_receipt(self.db,self.receipt,self.authority,b'fixture','2026-01-01T00:00:00')
    def test_forged_digest(self):
        self.db.execute('INSERT INTO evidence_bytes VALUES (?,?,?)',('0'*64,b'abc',3))
        self.assertFalse(verify_bytes(self.db,'0'*64))

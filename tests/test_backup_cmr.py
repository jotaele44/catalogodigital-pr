import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from prdc import connect,create
from prdc.backup import backup_v2,restore_v2
from prdc.cmr import parse_page,reconcile

class BackupCMRTests(unittest.TestCase):
    def test_backup_restore(self):
        with tempfile.TemporaryDirectory() as d:
            p,b,r=[Path(d)/x for x in ('source','backup','restore')]
            db=connect(p); key=create(db,'dataset','Fixture'); db.commit(); db.close()
            receipt=backup_v2(p,b)
            restore_v2(b,r,receipt)
            db=connect(r); self.assertEqual(db.execute('SELECT id FROM object').fetchone()[0],key); db.close()
            with self.assertRaises(FileExistsError): restore_v2(b,r,receipt)
    def test_tampered_backup(self):
        with tempfile.TemporaryDirectory() as d:
            p,b,r=[Path(d)/x for x in ('source','backup','restore')]
            db=connect(p); db.close()
            receipt=backup_v2(p,b)
            with b.open('ab') as f: f.write(b'tamper')
            with self.assertRaises(ValueError): restore_v2(b,r,receipt)
            self.assertFalse(r.exists())
    def page(self,cid,page=1):
        raw=json.dumps({'items':[{'meta':{'concept-id':cid,'revision-id':1},'umm':{'EntryTitle':'Fixture'}}]}).encode()
        return raw,dict(page=page,page_size=1,sha256=hashlib.sha256(raw).hexdigest(),byte_count=len(raw),cmr_hits='2')
    def test_cmr_native(self):
        self.assertEqual(parse_page(self.page('C123-TEST')[0])[0]['geographic_applicability'],'UNVERIFIED')
    def test_cmr_count(self):
        self.assertEqual(reconcile([self.page('C123-TEST'),self.page('C124-TEST',2)])['state'],'COUNT_MATCH_ONLY')
    def test_cmr_duplicate(self):
        with self.assertRaises(ValueError): reconcile([self.page('C123-TEST'),self.page('C123-TEST',2)])
    def test_cmr_tamper(self):
        raw,r=self.page('C123-TEST')
        with self.assertRaises(ValueError): reconcile([(raw+b' ',r)])

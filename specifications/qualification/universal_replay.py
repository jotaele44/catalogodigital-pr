"""Bounded synthetic checks only; no external source qualification."""
import json, sqlite3, unittest
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
root = Path(__file__).resolve().parents[1]
tax = json.loads((root/'taxonomy/universal-taxonomy-v0.3.0.json').read_text())
profiles = json.loads((root/'taxonomy/catalog-profile-crosswalk.json').read_text())['profiles']
legacy = json.loads((root/'baselines/prdc-r2/registry/seeds/domains.json').read_text())
schema = json.loads((root/'contracts/universal-candidate.schema.json').read_text())
sql = (root/'contracts/universal-candidate.sql').read_text()
i='11111111-1111-4111-8111-111111111111'
j='22222222-2222-4222-8222-222222222222'
k='33333333-3333-4333-8333-333333333333'
l='44444444-4444-4444-8444-444444444444'
stamp='2026-01-01T00:00:00Z'
digest='a'*64
class Qualification(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript(sql)
        self.db.execute('INSERT INTO resource VALUES (?,?,?,?,?)',(i,'dataset','Synthetic','CANDIDATE','DRAFT'))
        self.db.execute('INSERT INTO source_binding VALUES (?,?,?,?,?,?)',(j,i,'test','dataset','one','global'))
        self.db.execute('INSERT INTO receipt VALUES (?,?,?,?,?,?)',(k,j,stamp,digest,1,'synthetic'))
        self.v=Draft202012Validator(schema,format_checker=FormatChecker())
    def tearDown(self): self.db.close()
    def test_schema(self): Draft202012Validator.check_schema(schema)
    def test_taxonomy(self):
        nodes=tax['domains']+tax['subjects']
        ids={x['id'] for x in nodes}
        self.assertEqual(len(nodes),len(ids))
        self.assertEqual(len(tax['domains']),33)
        self.assertEqual(len(tax['subjects']),148)
        self.assertEqual({p for x in tax['subjects'] for p in x['parents']},{x['id'] for x in tax['domains']})
        self.assertTrue(all(p in ids for x in nodes for p in x.get('parents',[])+x.get('related_domains',[])))
        self.assertEqual({x['code']:x['label_en'] for x in legacy},{x['id']:x['label_en'] for x in tax['subjects'] if x['id'] in {y['code'] for y in legacy}})
        self.assertEqual(len({x['id'] for x in profiles}),74)
        self.assertTrue(all(p in ids for x in profiles for p in x['domains']))
    def test_resource_kinds(self):
        for kind in schema['$defs']['resource']['properties']['kind']['enum']:
            self.assertTrue(self.v.is_valid(dict(id=i,kind=kind,title='Synthetic',subjects=['K001'],classification='CANDIDATE',status='DRAFT')))
    def test_unearned_publish(self):
        self.assertFalse(self.v.is_valid(dict(id=i,kind='dataset',title='Synthetic',subjects=[],classification='CANDIDATE',status='PUBLISHED')))
    def test_rights_unknown(self):
        self.assertTrue(self.v.is_valid(dict(id=i,access='PUBLIC',redistribution='UNKNOWN',license_id=None,evidence_ref=None)))
    def test_temporal_shape(self):
        self.assertFalse(self.v.is_valid(dict(id=i,axis='OBSERVATION',start='invalid',end=None,precision='UNKNOWN')))
    def test_native_uniqueness(self):
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute('INSERT INTO source_binding VALUES (?,?,?,?,?,?)',(l,i,'test','dataset','one','global'))
    def test_receipt_immutable(self):
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute('UPDATE receipt SET byte_count=9 WHERE id=?',(k,))
    def test_receipt_delete(self):
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute('DELETE FROM receipt WHERE id=?',(k,))
    def test_receipt_negative(self):
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute('INSERT INTO receipt VALUES (?,?,?,?,?,?)',(l,j,stamp,digest,-1,'synthetic'))
    def test_version_self_reference(self):
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute('INSERT INTO version VALUES (?,?,?,?,?,?)',(l,i,'v1',l,k,'CANDIDATE'))
    def test_version_immutable(self):
        self.db.execute('INSERT INTO version VALUES (?,?,?,?,?,?)',(l,i,'v1',None,k,'CANDIDATE'))
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute('UPDATE version SET state=? WHERE id=?',('WITHDRAWN',l))
if __name__=='__main__': unittest.main(verbosity=2)

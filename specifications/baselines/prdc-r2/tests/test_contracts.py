import sqlite3, unittest, tempfile
from pathlib import Path
from prdc import connect, create, candidate_link, contract, access_contract, universe_coverage, ratio

class Contracts(unittest.TestCase):
 def setUp(self): self.db=connect()
 def tearDown(self): self.db.close()
 def obj(self,kind): return create(self.db,kind,kind)
 def rel(self,p,c,r): self.db.execute('INSERT INTO relation VALUES (?,?,?)',(p,c,r))
 def inst(self,kind='institution',native=None):
  k=self.obj(kind); self.db.execute('INSERT INTO institution_detail VALUES (?,?,?,?,?)',(k,'PR_MUNICIPAL','UNKNOWN',native,'synthetic' if native else None)); return k
 def snap(self,mode='CLOSED',count=2,receipt=True):
  u=self.obj('institutional_universe'); s=self.obj('denominator'); e=self.obj('source_receipt') if receipt else None
  self.db.execute('INSERT INTO universe VALUES (?,?,?)',(u,mode,'synthetic scope')); self.db.execute('INSERT INTO universe_snapshot VALUES (?,?,?,?,?)',(s,u,e,count,'2026-11-25T00:00:00Z')); return s
 def test_owner_closure(self):
  r=contract('logical_types.json'); names={x['name']:x for x in r}; self.assertEqual(len(names),73); self.assertEqual(len({x['code'] for x in r}),73)
  for x in r: self.assertEqual(names[x['owner']]['kind'],'logical_type'); self.assertEqual(names[x['owner']]['owner'],x['owner'])
 def test_metadata(self):
  m=contract('metadata.json'); self.assertEqual(len(m),19); self.assertEqual(len({x['field'] for x in m}),19); self.assertTrue(all(x['definition_es'] and x['definition_en'] for x in m))
 def test_vocabularies(self):
  self.assertEqual(len(contract('protocols.json')),15); self.assertEqual(len(contract('institutional_universe.json')['domains']),14)
  for name in ['formats.json','protocols.json']: self.assertEqual(len({x['code'] for x in contract(name)}),len(contract(name)))
 def test_unknown_kind(self):
  with self.assertRaises(sqlite3.IntegrityError): self.obj('invented')
 def test_view_not_object(self):
  with self.assertRaises(sqlite3.IntegrityError): self.obj('publisher')
 def test_type_immutable(self):
  with self.assertRaises(sqlite3.IntegrityError): self.db.execute("UPDATE object SET kind='source' WHERE id=?",(self.obj('dataset'),))
 def test_invalid_role(self):
  with self.assertRaises(sqlite3.IntegrityError): self.rel(self.obj('dataset'),self.obj('distribution'),'has')
 def test_wrong_types(self):
  with self.assertRaises(sqlite3.IntegrityError): self.rel(self.obj('dataset'),self.obj('endpoint'),'has_version')
 def test_version_owner(self):
  a,b,v=self.obj('dataset'),self.obj('document'),self.obj('dataset_version'); self.rel(a,v,'has_version')
  with self.assertRaises(sqlite3.IntegrityError): self.rel(b,v,'has_version')
 def test_distribution_owner(self):
  a,b,d=self.obj('dataset_version'),self.obj('dataset_version'),self.obj('distribution'); self.rel(a,d,'has_distribution')
  with self.assertRaises(sqlite3.IntegrityError): self.rel(b,d,'has_distribution')
 def test_shared_asset(self):
  a,b,d=self.obj('distribution'),self.obj('distribution'),self.obj('digital_asset'); self.rel(a,d,'has_file'); self.rel(b,d,'has_file')
 def test_hierarchy_cycle(self):
  a,b,c=[self.obj('organizational_unit') for _ in range(3)]; self.rel(a,b,'contains_unit'); self.rel(b,c,'contains_unit')
  with self.assertRaises(sqlite3.IntegrityError): self.rel(c,a,'contains_unit')
 def test_collection_cycle(self):
  a,b=self.obj('collection'),self.obj('collection'); self.rel(a,b,'collection_member')
  with self.assertRaises(sqlite3.IntegrityError): self.rel(b,a,'collection_member')
 def test_version_lineage(self):
  w=self.obj('dataset'); a,b=self.obj('dataset_version'),self.obj('dataset_version'); self.rel(w,a,'has_version'); self.rel(w,b,'has_version'); self.rel(b,a,'supersedes')
  with self.assertRaises(sqlite3.IntegrityError): self.rel(a,b,'supersedes')
  with self.assertRaises(sqlite3.IntegrityError): self.db.execute('DELETE FROM relation WHERE parent=? AND child=?',(w,a))
 def test_cross_work_lineage(self):
  a,b,v1,v2=self.obj('dataset'),self.obj('dataset'),self.obj('dataset_version'),self.obj('dataset_version'); self.rel(a,v1,'has_version'); self.rel(b,v2,'has_version')
  with self.assertRaises(sqlite3.IntegrityError): self.rel(v1,v2,'supersedes')
 def test_rule_immutable(self):
  with self.assertRaises(sqlite3.IntegrityError): self.db.execute('DELETE FROM relation_rule')
 def test_invalid_institution(self):
  with self.assertRaises(sqlite3.IntegrityError): self.inst('dataset')
 def test_institution_roles_aliases(self):
  i=self.inst(native='123'); self.db.execute('INSERT INTO institution_role VALUES (?,?)',(i,'PUBLISHER')); self.db.execute('INSERT INTO institution_role VALUES (?,?)',(i,'CUSTODIAN')); self.db.execute('INSERT INTO institution_alias VALUES (?,?)',(i,'Synthetic alias'))
  with self.assertRaises(sqlite3.IntegrityError): self.inst(native='123')
 def test_closed_coverage(self):
  s=self.snap(); self.db.execute('INSERT INTO universe_member VALUES (?,?,?)',(s,self.inst(),'IN_SCOPE')); self.db.execute('INSERT INTO universe_member VALUES (?,?,?)',(s,self.inst(),'UNRESOLVED')); r=universe_coverage(self.db,s); self.assertEqual(r['reconciliation'],1); self.assertEqual(r['classification'],.5); self.assertFalse(r['certified'])
 def test_open_coverage(self): self.assertIsNone(universe_coverage(self.db,self.snap('OPEN'))['reconciliation'])
 def test_missing_denominator(self): self.assertIsNone(universe_coverage(self.db,self.snap(count=None))['reconciliation'])
 def test_zero_denominator(self): self.assertIsNone(universe_coverage(self.db,self.snap(count=0))['reconciliation'])
 def test_missing_receipt(self): self.assertIsNone(universe_coverage(self.db,self.snap(receipt=False))['reconciliation'])
 def test_excess_membership(self):
  s=self.snap(count=1)
  for _ in range(2): self.db.execute('INSERT INTO universe_member VALUES (?,?,?)',(s,self.inst(),'IN_SCOPE'))
  self.assertIsNone(universe_coverage(self.db,s)['reconciliation'])
 def test_invalid_receipt_type(self):
  s=self.snap()
  with self.assertRaises(sqlite3.IntegrityError): self.db.execute('UPDATE universe_snapshot SET source_receipt=? WHERE id=?',(self.obj('dataset'),s))
 def test_access_vocab(self):
  for kw in [dict(access_class='RESTRICTED'),dict(scope='MAGIC'),dict(authorization='MAGIC'),dict(protocol='MAGIC'),dict(format_code='MAGIC')]:
   d={'access_class':'FILE','scope':'COMPLETE_FILE'}; d.update(kw)
   with self.subTest(kw=kw),self.assertRaises(sqlite3.IntegrityError): candidate_link(self.db,self.obj('endpoint'),'https://example.org/data',**d)
 def test_access_wrong_kind(self):
  with self.assertRaises(sqlite3.IntegrityError): candidate_link(self.db,self.obj('distribution'),'https://example.org/data','FILE','COMPLETE_FILE')
 def test_auth_independent(self):
  k=self.obj('endpoint'); candidate_link(self.db,k,'https://example.org/data','FILE','COMPLETE_FILE',authorization='AUTHENTICATED',format_code='CSV'); self.assertEqual(self.db.execute('SELECT class,authorization,status FROM access WHERE id=?',(k,)).fetchone(),('FILE','AUTHENTICATED','PENDING'))
 def test_secret_url(self):
  for u in ['https://user:pass@example.org/x','https://example.org/x?access_token=secret','https://example.org/x?X-Amz-Signature=secret','https://example.org:bad/x','https://example.org/x\n']:
   with self.subTest(u=u),self.assertRaises(ValueError): candidate_link(self.db,self.obj('endpoint'),u,'FILE','UNKNOWN')
 def test_reference_protocols(self):
  for p in contract('protocols.json'):
   with self.subTest(protocol=p['code']):
    k=self.obj('endpoint'); candidate_link(self.db,k,'https://example.org/fixture','QUERY','METADATA_ONLY',protocol=p['code']); self.assertEqual(self.db.execute('SELECT protocol,status FROM access WHERE id=?',(k,)).fetchone(),(p['code'],'PENDING')); self.assertEqual(p['qualification'],'NOT_TESTED_LIVE')
 def test_reopen(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'test.db'; db=connect(p); k=create(db,'dataset','synthetic'); db.commit(); db.close(); db=connect(p); self.assertEqual(db.execute('SELECT id FROM object').fetchone()[0],k); db.close()
 def test_no_silent_migration(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'old.db'; db=sqlite3.connect(p); db.execute('CREATE TABLE object(id TEXT)'); db.execute("INSERT INTO object VALUES ('preserve')"); db.commit(); db.close(); before=p.read_bytes()
   with self.assertRaises(ValueError): connect(p)
   self.assertEqual(p.read_bytes(),before)
 def test_noninteger_coverage(self):
  with self.assertRaises(ValueError): ratio(1.5,2)
 def test_direct_sql_rejects_secret_url(self):
  k=self.obj('endpoint')
  with self.assertRaises(sqlite3.IntegrityError): self.db.execute("INSERT INTO access(id,url,class,scope) VALUES (?,?,'FILE','UNKNOWN')",(k,'https://example.org/?access_token=secret'))
 def test_invalid_uuid_direct_sql(self):
  with self.assertRaises(sqlite3.IntegrityError): self.db.execute("INSERT INTO object VALUES ('not-a-uuid','dataset','synthetic')")
 def test_schema_drift(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'test.db'; db=connect(p); db.execute('DROP TRIGGER immutable_identity'); db.commit(); db.close()
   with self.assertRaisesRegex(ValueError,'drift'): connect(p)

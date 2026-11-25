import unittest, sqlite3, json
from pathlib import Path
from prdc import connect,create,candidate_link,ratio,eligible_for_verified_publication
class Foundation(unittest.TestCase):
 def setUp(self): self.db=connect(); self.a=create(self.db,'dataset','Synthetic'); self.b=create(self.db,'dataset_version','Synthetic'); self.e=create(self.db,'endpoint','Synthetic')
 def tearDown(self): self.db.close()
 def test_unique(self):
  with self.assertRaises(sqlite3.IntegrityError): self.db.execute('INSERT INTO object VALUES (?,?,?)',(self.a,'dataset','x'))
 def test_immutable(self):
  with self.assertRaises(sqlite3.IntegrityError): self.db.execute('UPDATE object SET id=? WHERE id=?',('new',self.a))
 def test_no_delete(self):
  with self.assertRaises(sqlite3.IntegrityError): self.db.execute('DELETE FROM object WHERE id=?',(self.a,))
 def test_fk(self):
  with self.assertRaises(sqlite3.IntegrityError): self.db.execute('INSERT INTO relation VALUES (?,?,?)',(self.a,'absent','has_version'))
 def test_relation(self): self.db.execute('INSERT INTO relation VALUES (?,?,?)',(self.a,self.b,'has_version'))
 def test_pending(self):
  candidate_link(self.db,self.e,'https://example.org/test.csv','FILE','UNKNOWN'); self.assertEqual(self.db.execute('SELECT status FROM access').fetchone()[0],'PENDING')
 def test_bad_url(self):
  with self.assertRaises(ValueError): candidate_link(self.db,self.e,'file:///etc/passwd','FILE','UNKNOWN')
 def test_no_promotion(self):
  candidate_link(self.db,self.e,'https://example.org/test.csv','FILE','UNKNOWN')
  with self.assertRaises(sqlite3.IntegrityError): self.db.execute("UPDATE access SET status='PASS'")
 def test_fail_closed(self): self.assertFalse(eligible_for_verified_publication({'status':'PASS'}))
 def test_ratio(self): self.assertEqual(ratio(3,4),.75); self.assertIsNone(ratio(0,0)); self.assertIsNone(ratio(0,None))
 def test_invalid_counts(self):
  with self.assertRaises(ValueError): ratio(2,1)
 def test_seeds(self):
  root=Path(__file__).resolve().parents[1]/'registry'/'seeds'
  for name,n in [('domains',120),('municipalities',78),('municipal_categories',40)]:
   items=json.loads((root/f'{name}.json').read_text()); self.assertEqual(len(items),n); self.assertEqual(len({json.dumps(x,sort_keys=True) for x in items}),n)

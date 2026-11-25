import json,sqlite3,unittest
from pathlib import Path
from semantic_controls import coarse_bounds,membership,geographic_candidate
root=Path(__file__).resolve().parents[1]
sql=(root/'contracts/universal-candidate.sql').read_text()
tax=json.loads((root/'taxonomy/universal-taxonomy-v0.3.0.json').read_text())
profiles=json.loads((root/'taxonomy/catalog-profile-crosswalk.json').read_text())['profiles']
class SemanticControls(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript(sql)
        for x in ('a','b'):
            self.db.execute("INSERT INTO resource VALUES (?, 'dataset','test','CANDIDATE','DRAFT')",(x,))
            self.db.execute("INSERT INTO source_binding VALUES (?,?, 'test','dataset',?,'scope')",('s'+x,x,x))
            self.db.execute("INSERT INTO receipt VALUES (?,?, '2026-01-01T00:00:00Z',?,1,'fixture')",('r'+x,'s'+x,'a'*64))
        self.db.execute("INSERT INTO version VALUES ('v','a','v1',NULL,'ra','CANDIDATE')")
    def tearDown(self): self.db.close()
    def test_year(self): self.assertEqual(coarse_bounds('2024','YEAR'),('2024-01-01','2025-01-01'))
    def test_leap_day(self): self.assertEqual(coarse_bounds('2024-02-29','DAY'),('2024-02-29','2024-03-01'))
    def test_month(self): self.assertEqual(coarse_bounds('2024-12','MONTH'),('2024-12-01','2025-01-01'))
    def test_bad_calendar(self):
        for value,precision in [('2023-02-29','DAY'),('2024-13','MONTH'),('2024-01','YEAR')]:
            with self.subTest(value=value),self.assertRaises(ValueError): coarse_bounds(value,precision)
    def test_membership(self):
        result=membership(['K011'],[],tax,profiles)
        self.assertIn('CDH',result)
        self.assertNotIn('CD-PRE',result)
    def test_facet_independent(self): self.assertIn('CD-PRE',membership(['K011'],['predictive_processing'],tax,profiles))
    def test_unknown_subject(self):
        with self.assertRaises(ValueError): membership(['K999'],[],tax,profiles)
    def test_geo_candidate(self): self.assertEqual(geographic_candidate('US_CENSUS_COUNTY_GEOID','72127','2025','receipt')['status'],'CANDIDATE')
    def test_geo_wrong_jurisdiction(self):
        with self.assertRaises(ValueError): geographic_candidate('US_CENSUS_COUNTY_GEOID','06037','2025','receipt')
    def test_foreign_version_receipt(self):
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute("INSERT INTO version VALUES ('v2','a','v2',NULL,'rb','CANDIDATE')")
    def test_lifecycle(self):
        self.db.execute("INSERT INTO version_event VALUES ('e1','v',1,'QUALIFIED','ra')")
        self.db.execute("INSERT INTO version_event VALUES ('e2','v',2,'WITHDRAWN','ra')")
        self.assertEqual(self.db.execute("SELECT state FROM version_current_state WHERE id='v'").fetchone()[0],'WITHDRAWN')
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute("INSERT INTO version_event VALUES ('e3','v',3,'QUALIFIED','ra')")
    def test_event_sequence(self):
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute("INSERT INTO version_event VALUES ('e1','v',2,'QUALIFIED','ra')")
    def test_event_foreign_evidence(self):
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute("INSERT INTO version_event VALUES ('e1','v',1,'QUALIFIED','rb')")
    def test_event_immutable(self):
        self.db.execute("INSERT INTO version_event VALUES ('e1','v',1,'QUALIFIED','ra')")
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute("DELETE FROM version_event WHERE id='e1'")
    def test_rights_foreign_evidence(self):
        self.db.execute("INSERT INTO rights VALUES ('x','PUBLIC','PERMITTED','test','rb')")
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute("INSERT INTO resource_rights VALUES ('a','x')")
    def test_rights_missing_evidence(self):
        self.db.execute("INSERT INTO rights VALUES ('x','PUBLIC','PERMITTED','test',NULL)")
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute("INSERT INTO resource_rights VALUES ('a','x')")
    def test_rights_unknown(self):
        self.db.execute("INSERT INTO rights VALUES ('x','PUBLIC','UNKNOWN',NULL,NULL)")
        self.db.execute("INSERT INTO resource_rights VALUES ('a','x')")
if __name__=='__main__': unittest.main(verbosity=2)

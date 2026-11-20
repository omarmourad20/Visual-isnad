"""Run from backend/isnad: python -m unittest discover -s tests -p 'test_source_crosswalk.py'"""
import importlib.util
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
for name in ('source_matching', 'source_crosswalk'):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
from source_matching import HadithRecord
from source_crosswalk import build_crosswalk, parse_record
def rec(provider, id, text, ref='1', book='صحيح البخاري'):
    return HadithRecord(provider, 'v1', id, book, text, ref)
class CrosswalkTests(unittest.TestCase):
    def test_reference_mismatch_still_candidate(self):
        r = build_crosswalk([rec('django','15','إِنَّمَا الْأَعْمَالُ','15')],[rec('kg','14','انما الاعمال','14')])
        self.assertEqual(r['counts']['candidate_pairs'],1)
        self.assertEqual(r['proposals'][0]['status'],'review_required')
    def test_identical_numbers_do_not_override_text(self):
        r = build_crosswalk([rec('django','15','قال زيد')],[rec('kg','15','قال عمر')])
        self.assertEqual(r['counts']['candidate_pairs'],0)
    def test_duplicate_text_is_ambiguous(self):
        r = build_crosswalk([rec('django','1','نص')],[rec('kg','2','نص'),rec('kg','3','نص')])
        self.assertEqual(r['counts']['ambiguous_left'],1)
        self.assertEqual(r['counts']['candidate_pairs'],2)
    def test_collection_scope(self):
        r = build_crosswalk([rec('django','1','نص')],[rec('kg','1','نص',book='سنن أبي داود')])
        self.assertEqual(r['counts']['candidate_pairs'],0)
    def test_missing_text(self):
        r = build_crosswalk([rec('django','1','')],[rec('kg','1','نص')])
        self.assertEqual(r['counts']['left_missing_text'],1)
    def test_invalid_input(self):
        with self.assertRaises(ValueError): parse_record({'native_id':'1'})
if __name__ == '__main__': unittest.main()

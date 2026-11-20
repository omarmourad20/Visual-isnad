"""Run: python -m unittest discover -s backend/isnad/tests -p 'test_source_matching.py'"""
import importlib.util
from pathlib import Path
import sys
import unittest

path = Path(__file__).resolve().parents[1] / "source_matching.py"
spec = importlib.util.spec_from_file_location("source_matching", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

def rec(provider, native_id, text, reference="1", collection="صحيح البخاري"):
    return module.HadithRecord(provider, "edition-a", native_id, collection, text, reference)

class MatchingTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(module.normalize_arabic("إِنَّمَا الأَعْمَالُ"), module.normalize_arabic("انما الاعمال"))
    def test_same_id_different_text(self):
        self.assertEqual(module.propose_match(rec("django","15","قال النبي"),rec("kg","15","قال عمر")).status,"not_matched")
    def test_same_text_different_reference_requires_review(self):
        p=module.propose_match(rec("django","15","إنما الأعمال","15"),rec("kg","14","انما الاعمال","14"))
        self.assertEqual(p.status,"review_required")
        self.assertFalse(p.reference_equal)
    def test_collection_mismatch(self):
        self.assertEqual(module.propose_match(rec("django","1","نص"),rec("kg","1","نص",collection="سنن أبي داود")).status,"not_matched")
    def test_missing_text(self):
        self.assertEqual(module.propose_match(rec("django","1",""),rec("kg","1","نص")).status,"insufficient_evidence")
    def test_provider_scoped_ids(self):
        p=module.propose_match(rec("django","1","نص"),rec("kg","1","نص"))
        self.assertNotEqual(p.left_key,p.right_key)

if __name__ == "__main__":
    unittest.main()

"""Conservative source matching tests."""
import unittest

from isnad import source_matching as module

def rec(provider, native_id, text, ref="1", collection="صحيح البخاري"):
    return module.HadithRecord(provider, "v1", native_id, collection, text, ref)

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
    def test_matn_agreement_does_not_hide_different_isnad_text(self):
        left = module.HadithRecord("visual", "v1", "1", "Bukhari", "نص", arabic_isnad="حدثنا زيد")
        right = module.HadithRecord("kg", "v2", "9", "Bukhari", "نص", arabic_isnad="حدثنا عمرو")
        proposal = module.propose_match(left, right)
        self.assertEqual(proposal.evidence, "matn")
        self.assertEqual(proposal.isnad_agreement, "text_differs")
        self.assertEqual(proposal.status, "review_required")

    def test_provider_scoped_ids(self):
        p=module.propose_match(rec("django","1","نص"),rec("kg","1","نص"))
        self.assertNotEqual(p.left_key,p.right_key)

if __name__ == "__main__":
    unittest.main()

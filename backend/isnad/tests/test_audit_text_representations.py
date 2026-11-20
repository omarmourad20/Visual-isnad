"""Django-independent representation diagnostic unit tests."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
pkg = types.ModuleType("isnad")
pkg.__path__ = [str(ROOT)]
sys.modules.setdefault("isnad", pkg)
for name in ("source_matching", "export_source_records", "audit_text_representations"):
    spec = importlib.util.spec_from_file_location("isnad." + name, ROOT / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
from isnad.audit_text_representations import classify, audit

class TextRepresentationTests(unittest.TestCase):
    def test_full_equal(self):
        self.assertEqual(classify("إِنَّمَا الْأَعْمَالُ", "الأعمال", "انما الاعمال"), "exact_full")
    def test_matn_equal(self):
        self.assertEqual(classify("حدثنا عمر قال إنما الأعمال", "إنما الأعمال", "انما الاعمال"), "exact_matn")
    def test_kg_substring_of_full(self):
        self.assertEqual(classify("حدثنا عمر قال إنما الأعمال", "", "انما الاعمال"), "kg_substring_of_full")
    def test_missing(self):
        self.assertEqual(classify("", "", "النص"), "missing_text")
    def test_different(self):
        self.assertEqual(classify("قال زيد", "قال زيد", "قال عمر"), "different_text")
    def test_number_mismatch_is_not_match(self):
        result = audit([(1, "15", "النص", "النص")], [(14, "14", "النص")])
        self.assertEqual(result["counts"]["no_same_number"], 1)
        self.assertNotIn("exact_full", result["counts"])
    def test_multiple_same_number_rows(self):
        result = audit([(1, "1", "النص", "")], [(10, "1", "النص"), (11, "1", "غيره")])
        self.assertEqual(result["counts"]["same_number_candidates"], 2)

if __name__ == "__main__":
    unittest.main()

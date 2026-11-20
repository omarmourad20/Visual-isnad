import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.benchmark_bukhari import concordance, connect, normalized, sort_ref


class BenchmarkTests(unittest.TestCase):
    def test_arabic_normalization_for_matching(self):
        self.assertEqual(normalized("‏إِنَّمَا، الأَعْمَالُ"), "إنما الأعمال")
        self.assertEqual(normalized("الفـصل"), "الفصل")
        self.assertNotEqual(normalized("إلى"), normalized("الى"))

    def test_candidates_do_not_assume_equal_ids_or_unique_text(self):
        local = {"1": ("نص", "Words.", "Book 1, Hadith 1")}
        rows = [
            ("1", "غير", "Other", "Book 1, Hadith 1"),
            ("9", "نص", "words", "Book 2, Hadith 7"),
            ("10", "نص", "new", ""),
        ]
        output = concordance(local, rows, ["1"])["sample"]["1"]
        self.assertEqual(output["arabic_text_candidates"], ["9", "10"])
        self.assertEqual(output["english_text_candidates"], ["9"])
        self.assertTrue(output["same_number_book_reference_agrees"])

    def test_readonly_database(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "data #.sqlite"
            with self.assertRaises(FileNotFoundError):
                connect(path)
            self.assertFalse(path.exists())
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE x (n INTEGER)")
            with connect(path) as db:
                self.assertEqual(db.execute("PRAGMA query_only").fetchone(), (1,))
                with self.assertRaises(sqlite3.OperationalError):
                    db.execute("INSERT INTO x VALUES (1)")

    def test_number_sort_preserves_suffixes(self):
        self.assertEqual(sorted(["1067", "15b", "15", "1"], key=sort_ref), ["1", "15", "15b", "1067"])


class KnowledgeGraphAuditTests(unittest.TestCase):
    def test_edition_offset_and_ordered_routes(self):
        from scripts.audit_knowledge_graph import audit

        with sqlite3.connect(":memory:") as db:
            db.executescript("""
                CREATE TABLE books (id, name, tabaa);
                CREATE TABLE hadiths (id, book_id, no_inbook, nass, type, group_id, takhrij);
                CREATE TABLE rawis (id, name, nickname, rank);
                CREATE TABLE sanads (id, hadith_id);
                CREATE TABLE sanad_rawis (sanad_id, pos, rawi_id);
                CREATE TABLE hadith_rawis (rawi_id);
                CREATE TABLE aqwal (id);
                CREATE TABLE meaning_groups (id);
                INSERT INTO books VALUES (1, 'صحيح البخاري', 'test');
                INSERT INTO hadiths VALUES (14, 1, 14, 'قول الراوي عن صاحبه', 'مرفوع', NULL, NULL);
                INSERT INTO rawis VALUES (9, 'المصنف', '', ''), (10, 'الراوي', '', '');
                INSERT INTO sanads VALUES (29, 14), (30, 14);
                INSERT INTO sanad_rawis VALUES (29, 1, 10), (29, 0, 9), (30, 0, 9), (30, 1, 10);
            """)
            result = audit(db, {"15": ("قول الراوي عن صاحبه", "", "")}, ["15"], None)
        candidate = result["sample"]["15"]["14"]
        self.assertTrue(candidate["normalized_full_text_exact"])
        self.assertEqual(list(candidate["sanads"]), [29, 30])
        self.assertEqual(candidate["sanads"][29], [(0, 9, "المصنف"), (1, 10, "الراوي")])
        self.assertEqual(result["book_rows_with_multiple_sanads"], 1)
        self.assertEqual(result["orphan_chain_narrator_positions"], 0)

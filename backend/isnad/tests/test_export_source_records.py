"""Read-only SQLite export tests, using temporary synthetic databases."""
import importlib.util
import sqlite3
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("export_source_records", ROOT / "export_source_records.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "sample.sqlite3"
    def tearDown(self):
        self.tmp.cleanup()
    def test_visual_export(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE isnad_hadith (id INTEGER, hadith_number TEXT, book_title TEXT, arabic_full TEXT, arabic_matn TEXT, in_book_reference TEXT)")
            db.execute("INSERT INTO isnad_hadith VALUES (1,'15','Sahih al-Bukhari','النص الكامل','النص','Book 1, Hadith 15')")
            db.execute("INSERT INTO isnad_hadith VALUES (2,'1','Sahih Muslim','آخر','','')")
        with module.readonly_connection(self.path) as db:
            rows = module.export_records(db,"visual","snapshot-1")
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("INSERT INTO isnad_hadith VALUES (3,'','','','','')")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["native_id"],"1")
        self.assertEqual(rows[0]["arabic_matn"],"النص الكامل")
    def test_kg_export(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE books (id INTEGER, name TEXT)")
            db.execute("CREATE TABLE hadiths (id INTEGER, book_id INTEGER, no_inbook TEXT, nass TEXT)")
            db.execute("INSERT INTO books VALUES (1,'صحيح البخاري')")
            db.execute("INSERT INTO hadiths VALUES (14,1,'14','النص')")
        with module.readonly_connection(self.path) as db:
            rows = module.export_records(db,"kg","release-1")
        self.assertEqual(rows[0]["native_id"],"14")
        self.assertEqual(rows[0]["printed_reference"],"14")
    def test_reject_wrong_kg_book(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE books (id INTEGER, name TEXT)")
            db.execute("CREATE TABLE hadiths (id INTEGER, book_id INTEGER, no_inbook TEXT, nass TEXT)")
            db.execute("INSERT INTO books VALUES (1,'سنن أبي داود')")
        with module.readonly_connection(self.path) as db:
            with self.assertRaises(ValueError): module.export_records(db,"kg","release-1")
    def test_missing_file_does_not_create_db(self):
        with self.assertRaises(FileNotFoundError): module.readonly_connection(self.path)
        self.assertFalse(self.path.exists())

if __name__ == "__main__": unittest.main()

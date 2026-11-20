"""Export hadith texts from SQLite snapshots without modifying either database.

Usage:
 python -m isnad.export_source_records --source visual --db visual.sqlite3 --output visual.json
 python -m isnad.export_source_records --source kg --db hadith-kg.db --output kg.json --book-id 1

Outputs are candidate inputs, not validated equivalences.
"""
import argparse
import json
import sqlite3
from pathlib import Path

BUKHARI = "صحيح البخاري"

def readonly_connection(path):
    uri = Path(path).resolve(strict=True).as_uri() + "?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    try:
        db.execute("PRAGMA query_only=ON")
        return db
    except BaseException:
        db.close()
        raise

def export_visual(db, edition):
    cursor = db.execute("""
        SELECT id, hadith_number, book_title, arabic_full, arabic_matn,
               in_book_reference FROM isnad_hadith ORDER BY id
    """)
    for pk, number, book, full, matn, reference in cursor:
        if not book or "bukhari" not in book.casefold() and "البخاري" not in book:
            continue
        yield dict(provider="visual_isnad", edition=edition, native_id=str(pk),
                   collection=BUKHARI, arabic_matn=(full or matn or ""),
                   printed_reference=str(reference or number or ""))

def export_kg(db, edition, book_id):
    book = db.execute("SELECT name FROM books WHERE id=?", (book_id,)).fetchone()
    if not book or "البخاري" not in book[0]:
        raise ValueError("KG book ID must identify Sahih al-Bukhari; inspect books table first")
    for pk, number, text in db.execute(
        "SELECT id, no_inbook, nass FROM hadiths WHERE book_id=? ORDER BY id", (book_id,)
    ):
        yield dict(provider="hadith_kg", edition=edition, native_id=str(pk),
                   collection=BUKHARI, arabic_matn=text or "",
                   printed_reference=str(number or ""))

def export_records(db, source, edition, book_id=1):
    if source == "visual":
        return list(export_visual(db, edition))
    if source == "kg":
        return list(export_kg(db, edition, book_id))
    raise ValueError("Unknown source")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["visual", "kg"], required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--edition", required=True, help="Explicit edition or snapshot identifier")
    parser.add_argument("--book-id", type=int, default=1)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error("Output already exists; refusing to overwrite")
    with readonly_connection(args.db) as db:
        records = export_records(db, args.source, args.edition, args.book_id)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Exported {len(records)} records to {output}")

if __name__ == "__main__":
    main()

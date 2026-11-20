"""Export hadith texts from SQLite snapshots without modifying either database.

Usage:
 python -m isnad.export_source_records --source visual --db visual.sqlite3 --output visual.json
 python -m isnad.export_source_records --source kg --db hadith-kg.db --output kg.json --book-id 1

Outputs are candidate inputs, not validated equivalences.
"""
import argparse
import json
from contextlib import closing
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
    columns = {row[1] for row in db.execute("PRAGMA table_info(isnad_hadith)")}
    isnad_column = "arabic_isnad" if "arabic_isnad" in columns else "NULL"
    cursor = db.execute(f"""
        SELECT id, hadith_number, book_title, arabic_full, arabic_matn,
               in_book_reference, {isnad_column} FROM isnad_hadith ORDER BY id
    """)
    for pk, number, book, full, matn, reference, isnad in cursor:
        if not book or "bukhari" not in book.casefold() and "البخاري" not in book:
            continue
        yield dict(provider="visual_isnad", edition=edition, native_id=str(pk),
                   collection=BUKHARI, arabic_matn=matn or "", arabic_full=full or "", arabic_isnad=isnad or "",
                   printed_reference=str(reference or number or ""))

def export_kg(db, edition, book_id):
    book = db.execute("SELECT name FROM books WHERE id=?", (book_id,)).fetchone()
    if not book or book[0].strip() != BUKHARI:
        raise ValueError("KG book ID must identify Sahih al-Bukhari; inspect books table first")
    columns = {row[1] for row in db.execute("PRAGMA table_info(hadiths)")}
    offsets = "matn_start, matn_end" if {"matn_start", "matn_end"} <= columns else "NULL, NULL"
    for pk, number, text, start, end in db.execute(
        f"SELECT id, no_inbook, nass, {offsets} FROM hadiths WHERE book_id=? ORDER BY id", (book_id,)
    ):
        matn = span_matn(text, start, end)
        yield dict(provider="hadith_kg", edition=edition, native_id=str(pk), collection=BUKHARI,
                   arabic_full=text or "", arabic_matn=matn, arabic_isnad=text[:start] if matn else "",
                   printed_reference=str(number or ""))


def span_matn(text, start, end):
    if text and type(start) is int and type(end) is int and 0 <= start < end <= len(text):
        return text[start:end]
    return ""


def export_json(path, source, edition):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if source == "jaguar":
        if data["collection"]["id"] != "bukhari":
            raise ValueError("Expected a Jaguar Bukhari release file")
        rows = ((row["hadith_number"], row["text_ar"], row.get("matn_ar"), row.get("reference"), row.get("isnad_ar"))
                for book in data["books"] for row in book["hadiths"])
    else:
        if data["metadata"]["name"] != "Sahih al Bukhari":
            raise ValueError("Expected a Fawaz Arabic Bukhari edition")
        rows = ((row["hadithnumber"], row["text"], "", row["hadithnumber"], "") for row in data["hadiths"])
    return [
        dict(provider=source, edition=edition, native_id=str(key), collection=BUKHARI,
             arabic_full=full or "", arabic_matn=matn or "", arabic_isnad=isnad or "", printed_reference=str(ref or ""))
        for key, full, matn, ref, isnad in rows
        if full and any("\u0600" <= char <= "\u06ff" for char in full)
    ]


def export_records(db, source, edition, book_id=1):
    if source == "visual":
        return list(export_visual(db, edition))
    if source == "kg":
        return list(export_kg(db, edition, book_id))
    raise ValueError("Unknown source")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["visual", "kg", "fawaz", "jaguar"], required=True)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--db")
    inputs.add_argument("--json")
    parser.add_argument("--edition", required=True, help="Explicit edition or snapshot identifier")
    parser.add_argument("--book-id", type=int, default=1)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error("Output already exists; refusing to overwrite")
    if args.source in {"visual", "kg"}:
        if not args.db:
            parser.error("SQLite sources require --db")
        with closing(readonly_connection(args.db)) as db:
            records = export_records(db, args.source, args.edition, args.book_id)
    else:
        if not args.json:
            parser.error("Release sources require --json")
        records = export_json(args.json, args.source, args.edition)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Exported {len(records)} records to {output}")

if __name__ == "__main__":
    main()

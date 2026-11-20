"""Inspect a published Hadith Knowledge Graph relational SQLite release read-only."""
import argparse
import json
from collections import Counter, defaultdict
from difflib import SequenceMatcher

if __package__:
    from .benchmark_bukhari import concordance, connect, normalized
else:
    from benchmark_bukhari import concordance, connect, normalized


def audit(db, visual, sample, book_id):
    books = list(db.execute("SELECT id,name,tabaa FROM books ORDER BY id"))
    if book_id is None:
        candidates = [row for row in books if normalized(row[1]) in {"صحيح البخاري", "الجامع الصحيح للبخاري"}]
        if len(candidates) != 1:
            raise ValueError(f"Select --book-id after reviewing candidate books: {candidates}")
        book_id = candidates[0][0]
    book = next((row for row in books if row[0] == book_id), None)
    if book is None:
        raise ValueError(f"Book {book_id} is absent")

    global_counts = {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in (
        "books", "hadiths", "rawis", "sanads", "sanad_rawis", "aqwal", "meaning_groups",
    )}
    rows = list(db.execute(
        "SELECT id,no_inbook,nass,type,group_id,takhrij FROM hadiths WHERE book_id=? ORDER BY id", (book_id,)
    ))
    by_number = defaultdict(list)
    by_id = {}
    for row in rows:
        by_number[str(row[1])].append(row)
        by_id[str(row[0])] = row
    matches = concordance(visual, ((str(row[0]), row[2], "", "") for row in rows), sample)
    chains = defaultdict(lambda: defaultdict(list))
    for hadith, sanad, pos, rawi, name in db.execute("""
        SELECT h.id, s.id, sr.pos, sr.rawi_id, r.name
        FROM hadiths h JOIN sanads s ON s.hadith_id=h.id
        LEFT JOIN sanad_rawis sr ON sr.sanad_id=s.id LEFT JOIN rawis r ON r.id=sr.rawi_id
        WHERE h.book_id=? ORDER BY h.id,s.id,sr.pos
    """, (book_id,)):
        chains[hadith][sanad]
        if rawi is not None:
            chains[hadith][sanad].append((pos, rawi, name))
    source_text = {str(row[0]): normalized(row[2]) for row in rows}
    def shingles(text):
        words = text.split()
        return set(zip(words, words[1:], words[2:]))
    index = defaultdict(list)
    for key, text in source_text.items():
        for phrase in shingles(text):
            index[phrase].append(key)

    sample_results = {}
    for ref in sample:
        candidates = matches["sample"][ref]["arabic_text_candidates"]
        same_number = by_number.get(ref, [])
        text = normalized(visual[ref][0])
        overlap = Counter(key for phrase in shingles(text) for key in index.get(phrase, ()))
        shortlist = [key for key, _ in sorted(overlap.items(), key=lambda item: (-item[1], int(item[0])))[:12]]
        def similarity(key):
            return SequenceMatcher(None, text, source_text[key], autojunk=False).ratio()
        ranked = sorted(shortlist, key=lambda key: (-similarity(key), int(key)))[:3]
        candidate_results = {}
        for kg_id in dict.fromkeys([*candidates, *ranked, *(str(row[0]) for row in same_number)]):
            row = by_id[kg_id]
            ratio = similarity(kg_id)
            candidate_results[kg_id] = {
                "number_in_kg_edition": row[1], "normalized_full_text_exact": kg_id in candidates,
                "text_similarity": round(ratio, 4), "report_type": row[3], "meaning_group": row[4],
                "takhrij": row[5], "sanads": dict(chains[row[0]]),
            }
        sample_results[ref] = candidate_results

    return {
        "book": book, "global_counts": global_counts, "book_rows": len(rows),
        "duplicate_book_number_groups": sum(len(group) > 1 for group in by_number.values()),
        "book_rows_with_sanads": len(chains),
        "book_rows_with_multiple_sanads": sum(len(group) > 1 for group in chains.values()),
        "book_sanads": sum(map(len, chains.values())),
        "book_sanads_without_nodes": sum(not route for group in chains.values() for route in group.values()),
        "bukhari_terminal_labels": Counter((route[-1][2] or "(missing)") for group in chains.values()
                                          for route in group.values() if route).most_common(12),
        "exact_prophet_title_rows": list(db.execute("""SELECT id,name,nickname,rank FROM rawis
            WHERE name IN ('رسول الله','النبي','محمد رسول الله')
               OR nickname IN ('رسول الله','النبي','محمد رسول الله')""")),
        "live_example_record": db.execute("""SELECT h.id,b.name,h.no_inbook,COUNT(s.id)
            FROM hadiths h JOIN books b ON h.book_id=b.id LEFT JOIN sanads s ON s.hadith_id=h.id
            WHERE h.id=17154 GROUP BY h.id""").fetchone(),
        "orphan_chain_narrator_positions": db.execute("""
            SELECT count(*) FROM sanad_rawis sr LEFT JOIN rawis r ON r.id=sr.rawi_id WHERE r.id IS NULL
        """).fetchone()[0],
        "sample": sample_results,
        "orphan_inline_narrator_mentions": db.execute("""
            SELECT count(*) FROM hadith_rawis hr LEFT JOIN rawis r ON r.id=hr.rawi_id
            WHERE hr.rawi_id IS NOT NULL AND r.id IS NULL
        """).fetchone()[0],
        "visual_refs_with_any_exact_arabic_match": matches["local_refs_with_any_exact_arabic_match"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kg", required=True)
    parser.add_argument("--visual", required=True)
    parser.add_argument("--samples", required=True, help="JSON report from benchmark_bukhari.py")
    parser.add_argument("--book-id", type=int)
    args = parser.parse_args()
    with open(args.samples, encoding="utf-8") as handle:
        sample = json.load(handle)["sample_refs"]
    with connect(args.visual) as db:
        visual = {ref: (ar, en, book) for ref, ar, en, book in db.execute(
            "SELECT hadith_number,arabic_full,english_matn,in_book_reference FROM isnad_hadith"
        )}
    with connect(args.kg) as db:
        result = audit(db, visual, sample, args.book_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

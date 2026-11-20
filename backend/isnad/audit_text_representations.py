"""Read-only diagnostics for comparing Arabic text representations.

Do not strip an isnad by heuristic or treat substring matches as reviewed identities.
Run from backend: python -m isnad.audit_text_representations --visual-db db.sqlite3 --kg-db kg.sqlite3 --output text-audit.json
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from .export_source_records import readonly_connection
from .source_matching import normalize_arabic

def classify(visual_full, visual_matn, kg_nass):
    full = normalize_arabic(visual_full)
    matn = normalize_arabic(visual_matn)
    kg = normalize_arabic(kg_nass)
    if not kg or not (full or matn):
        return "missing_text"
    if full and full == kg:
        return "exact_full"
    if matn and matn == kg:
        return "exact_matn"
    if full and kg in full:
        return "kg_substring_of_full"
    if matn and kg in matn:
        return "kg_substring_of_matn"
    if full and full in kg:
        return "full_substring_of_kg"
    if matn and matn in kg:
        return "matn_substring_of_kg"
    return "different_text"

def audit(visual_rows, kg_rows, max_examples=10):
    """Reference-only diagnostic; edition numbers are not reliable hadith identities."""
    by_ref = {}
    for kg_id, number, nass in kg_rows:
        by_ref.setdefault(str(number), []).append((kg_id, nass))
    counts = Counter()
    examples = []
    for visual_id, number, full, matn in visual_rows:
        candidates = by_ref.get(str(number), [])
        if not candidates:
            counts["no_same_number"] += 1
            continue
        counts["same_number_candidates"] += len(candidates)
        for kg_id, nass in candidates:
            category = classify(full, matn, nass)
            counts[category] += 1
            if len(examples) < max_examples:
                examples.append({"visual_id": visual_id, "visual_number": str(number),
                                 "kg_id": kg_id, "category": category})
    return {"warning": "Same-number comparisons are diagnostics, not crosswalk matches.",
            "counts": dict(sorted(counts.items())), "examples": examples}

def run(visual_path, kg_path, book_id=1, max_examples=10):
    with readonly_connection(visual_path) as visual:
        visual_rows = list(visual.execute(
            "SELECT id,hadith_number,arabic_full,arabic_matn FROM isnad_hadith ORDER BY id"))
    with readonly_connection(kg_path) as kg:
        book = kg.execute("SELECT name FROM books WHERE id=?", (book_id,)).fetchone()
        if not book or "البخاري" not in book[0]:
            raise ValueError("Selected KG book must be Sahih al-Bukhari")
        kg_rows = list(kg.execute(
            "SELECT id,no_inbook,nass FROM hadiths WHERE book_id=? ORDER BY id", (book_id,)))
    return audit(visual_rows, kg_rows, max_examples)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--visual-db", required=True)
    parser.add_argument("--kg-db", required=True)
    parser.add_argument("--book-id", type=int, default=1)
    parser.add_argument("--max-examples", type=int, default=10)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.max_examples < 0:
        parser.error("--max-examples must be non-negative")
    output = Path(args.output)
    if output.exists():
        parser.error("Output already exists; refusing to overwrite")
    result = run(args.visual_db, args.kg_db, args.book_id, args.max_examples)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(result["counts"], ensure_ascii=False))

if __name__ == "__main__":
    main()

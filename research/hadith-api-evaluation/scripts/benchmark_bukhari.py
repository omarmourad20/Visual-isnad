"""Report source coverage and text concordance without writing to any database."""
import argparse
import csv
import json
import random
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path

ANCHORS = ("1", "5", "15", "32", "74", "94", "188", "765", "1067", "7478")
SEED = 17154


def normalized(text):
    folded = unicodedata.normalize("NFC", text or "").casefold()
    return " ".join("".join(
        char if char.isalnum() and char != "ـ" else "" if unicodedata.category(char) in {"Mn", "Cf"} or char == "ـ" else " "
        for char in folded
    ).split())


def connect(path):
    uri = Path(path).resolve(strict=True).as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.execute("PRAGMA query_only=ON")
    return closing(connection)


def bukhari_rows(path, layout):
    if layout in {"mhashim", "mhashim_vocalized"}:
        with Path(path).open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.reader(handle):
                if len(row) >= 2:
                    yield row[0], row[1], "", ""
    else:
        with Path(path).open(encoding="utf-8") as handle:
            data = json.load(handle)
        if layout == "jaguar":
            for book in data["books"]:
                for row in book["hadiths"]:
                    yield str(row["hadith_number"]), row["text_ar"], row["text_en"], row.get("in_book_reference") or ""
        else:
            for row in data["hadiths"]:
                ref = row.get("reference") or {}
                book_ref = f'Book {ref["book"]}, Hadith {ref["hadith"]}' if {"book", "hadith"} <= ref.keys() else ""
                ar, en = (row["text"], "") if layout == "fawaz_ar" else ("", row["text"])
                yield str(row["hadithnumber"]), ar, en, book_ref


def sort_ref(value):
    match = re.fullmatch(r"(\d+)(.*)", value)
    return (int(match[1]), match[2]) if match else (0, value)


def concordance(local, rows, sample):
    identifiers = Counter()
    ar_index, en_index = defaultdict(list), defaultdict(list)
    same_number = defaultdict(list)
    for ref, ar, en, book_ref in rows:
        identifiers[ref] += 1
        ar, en = normalized(ar), normalized(en)
        if ar:
            ar_index[ar].append(ref)
        if en:
            en_index[en].append(ref)
        same_number[ref].append((ar, en, book_ref))

    def match(ref):
        ar, en, book_ref = local[ref][:3]
        ar, en = normalized(ar), normalized(en)
        return {
            "arabic_text_candidates": ar_index.get(ar, []),
            "english_text_candidates": en_index.get(en, []),
            "same_number_book_reference_agrees": bool(book_ref and any(
                candidate[2] == book_ref for candidate in same_number.get(ref, [])
            )),
        }

    return {
        "rows": sum(identifiers.values()),
        "distinct_ids": len(identifiers),
        "duplicate_id_groups": sum(count > 1 for count in identifiers.values()),
        "nonempty_arabic": sum(map(len, ar_index.values())),
        "nonempty_english": sum(map(len, en_index.values())),
        "repeated_arabic_text_groups": sum(len(ids) > 1 for ids in ar_index.values()),
        "local_refs_with_any_exact_arabic_match": sum(normalized(row[0]) in ar_index for row in local.values()),
        "local_refs_with_any_exact_english_match": sum(normalized(row[1]) in en_index for row in local.values()),
        "sample": {ref: match(ref) for ref in sample},
    }


def benchmark(args):
    with connect(args.visual) as db:
        local = {ref: (ar, en, book, pk) for pk, ref, ar, en, book in db.execute(
            "SELECT id,hadith_number,arabic_full,english_matn,in_book_reference FROM isnad_hadith"
        )}
        sample = [ref for ref in ANCHORS if ref in local]
        sample += random.Random(SEED).sample(
            sorted(local.keys() - set(sample), key=sort_ref), min(args.random_count, len(local) - len(sample))
        )
        routes = defaultdict(lambda: defaultdict(list))
        placeholders = 0
        for hadith, chain, student, teacher in db.execute(
            "SELECT hadith_id,chain_index,student_id,teacher_id FROM isnad_transmissionedge ORDER BY hadith_id,sequence"
        ):
            routes[hadith][chain].append((student, teacher))
            placeholders += teacher >= 800000
        result = {
            "seed": SEED,
            "sample_refs": sample,
            "visual": {
                "hadiths": len(local),
                "narrators": db.execute("SELECT count(*) FROM isnad_narrator").fetchone()[0],
                "edges": sum(len(route) for chains in routes.values() for route in chains.values()),
                "multiple_route_hadiths": sum(len(chains) > 1 for chains in routes.values()),
                "hadiths_without_edges": len(local) - len(routes),
                "hadiths_with_prophet_edge": sum(any(t == 1 for route in chains.values() for _, t in route)
                                                for chains in routes.values()),
                "unresolved_teacher_edges": placeholders,
                "foreign_key_violations": len(list(db.execute("PRAGMA foreign_key_check"))),
                "sample": {ref: {
                    "book_reference": local[ref][2],
                    "paths_student_to_teacher": list(routes.get(local[ref][3], {}).values()),
                } for ref in sample},
            },
            "sources": {},
        }
    for layout in ("mhashim", "mhashim_vocalized", "jaguar", "fawaz_ar", "fawaz_en"):
        path = getattr(args, layout)
        if path:
            result["sources"][layout] = concordance(local, bukhari_rows(path, layout), sample)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--visual", required=True)
    for name in ("mhashim", "mhashim-vocalized", "jaguar", "fawaz-ar", "fawaz-en"):
        parser.add_argument("--" + name)
    parser.add_argument("--random-count", type=int, default=8)
    args = parser.parse_args()
    if args.random_count < 0:
        parser.error("--random-count must be nonnegative")
    print(json.dumps(benchmark(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Validate a built Visual Isnad SQLite database without modifying it."""

import argparse
import csv
import json
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path


DATA = Path(__file__).resolve().parent.parent / "data"
UNRESOLVED_ID = 800000
EXPECTED_1067 = [30001, 30160, 20278, 20020, 11049, 11054, 16]


def read_only(path):
    return closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True))


def import_counts(db):
    return {
        "hadiths": db.execute("SELECT COUNT(*) FROM isnad_hadith").fetchone()[0],
        "narrators": db.execute("SELECT COUNT(*) FROM isnad_narrator").fetchone()[0],
        "canonical_narrators": db.execute(
            "SELECT COUNT(*) FROM isnad_narrator WHERE id < ?", (UNRESOLVED_ID,)
        ).fetchone()[0],
        "edges": db.execute("SELECT COUNT(*) FROM isnad_transmissionedge").fetchone()[0],
        "unresolved_edges": db.execute(
            "SELECT COUNT(*) FROM isnad_transmissionedge WHERE teacher_id >= ?", (UNRESOLVED_ID,)
        ).fetchone()[0],
        "nonempty_biographies": db.execute(
            "SELECT COUNT(*) FROM isnad_narrator WHERE id < ? AND TRIM(biography) <> ''",
            (UNRESOLVED_ID,),
        ).fetchone()[0],
    }


def catalog(db):
    return dict(db.execute("SELECT hadith_number, reference_url FROM isnad_hadith"))


def rawis_ids(db):
    return {row[0] for row in db.execute("SELECT id FROM isnad_narrator WHERE id < ?", (UNRESOLVED_ID,))}


def edges_for_1067(db):
    return [list(pair) for pair in db.execute("""
        SELECT edge.student_id, edge.teacher_id
        FROM isnad_transmissionedge AS edge
        JOIN isnad_hadith AS hadith ON hadith.id = edge.hadith_id
        WHERE hadith.hadith_number = '1067'
        ORDER BY edge.sequence
    """)]


def date_from_db(year, display):
    return -abs(year) if year is not None and " BH" in display.upper() else year


def validate(db, rawis, bukhari):
    with rawis.open(encoding="utf-8-sig", newline="") as source:
        rawis_rows = list(csv.DictReader(source))
    ids = Counter(int(row["scholar_indx"]) for row in rawis_rows)
    source_relationships = {
        int(row["scholar_indx"]): tuple(row.get(field) or "" for field in ("parents", "teachers_inds", "students_inds"))
        for row in rawis_rows
    }
    stored_relationships = {
        sid: (parents, teachers, students)
        for sid, parents, teachers, students in db.execute(
            "SELECT id, parents, teachers_inds, students_inds FROM isnad_narrator WHERE id < ?",
            (UNRESOLVED_ID,),
        )
    }
    with bukhari.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    expected_refs = {
        row["Reference"].strip().rsplit(":", 1)[-1].lower(): row["Reference"].strip()
        for row in rows
    }
    references = catalog(db)
    canonical = rawis_ids(db)
    failures = {
        "sqlite_integrity": [row[0] for row in db.execute("PRAGMA integrity_check") if row[0] != "ok"],
        "foreign_key_violations": list(db.execute("PRAGMA foreign_key_check")),
        "duplicate_source_narrator_ids": [key for key, count in ids.items() if count > 1],
        "missing_canonical_narrators": sorted(ids.keys() - canonical),
        "unexpected_canonical_narrators": sorted(canonical - ids.keys()),
        "changed_relationship_metadata": sorted(
            sid for sid in canonical & ids.keys()
            if stored_relationships[sid] != source_relationships[sid]
        ),
        "missing_or_changed_references": sorted(key for key, url in expected_refs.items() if references.get(key) != url),
        "unexpected_references": sorted(references.keys() - expected_refs.keys()),
        "duplicate_reference_count": len(rows) - len(expected_refs),
        "stored_duplicate_reference_count": import_counts(db)["hadiths"] - len(references),
        "invalid_edges": [],
        "broken_chains": [],
        "repeated_narrators_in_chain": [],
        "non_overlapping_lifetimes": [],
    }
    duplicate_name_groups = db.execute("""
        SELECT COUNT(*) FROM (
            SELECT arabic_name, birth_year, death_year FROM isnad_narrator
            WHERE id < ? AND TRIM(arabic_name) <> ''
            GROUP BY arabic_name, birth_year, death_year HAVING COUNT(*) > 1
        )
    """, (UNRESOLVED_ID,)).fetchone()[0]
    dates = {}
    for sid, birth, death, birth_display, death_display in db.execute(
        "SELECT id, birth_year, death_year, birth_display, death_display FROM isnad_narrator"
    ):
        bounds = (date_from_db(birth, birth_display), date_from_db(death, death_display))
        if bounds[0] is not None and bounds[1] is not None and bounds[0] > bounds[1]:
            bounds = (None, None)
        dates[sid] = bounds
    chain_counts = Counter()
    visited = set()
    last_hadith = last_chain = last_sequence = prior_teacher = None
    for hadith, chain, sequence, teacher, student in db.execute("""
        SELECT h.hadith_number, e.chain_index, e.sequence, e.teacher_id, e.student_id
        FROM isnad_transmissionedge e JOIN isnad_hadith h ON h.id = e.hadith_id
        ORDER BY e.hadith_id, e.sequence
    """):
        expected_sequence = last_sequence + 1 if hadith == last_hadith else 0
        if teacher == student or chain is None or sequence != expected_sequence:
            failures["invalid_edges"].append([hadith, sequence])
        if (hadith, chain) != (last_hadith, last_chain):
            visited = {student}
            chain_counts[hadith] += 1
            if chain != chain_counts[hadith] - 1:
                failures["broken_chains"].append([hadith, chain, sequence])
        elif student != prior_teacher:
            failures["broken_chains"].append([hadith, chain, sequence])
        if teacher in visited:
            failures["repeated_narrators_in_chain"].append([hadith, sequence, teacher])
        visited.add(teacher)
        student_birth, student_death = dates.get(student, (None, None))
        teacher_birth, teacher_death = dates.get(teacher, (None, None))
        if (
            student_birth is not None and teacher_death is not None and student_birth > teacher_death
            or teacher_birth is not None and student_death is not None and teacher_birth > student_death
        ):
            failures["non_overlapping_lifetimes"].append([hadith, sequence, student, teacher])
        last_hadith, last_chain, last_sequence, prior_teacher = hadith, chain, sequence, teacher
    sample = edges_for_1067(db)
    failures["hadith_1067_mismatch"] = sample != [
        list(pair) for pair in zip(EXPECTED_1067[:-1], EXPECTED_1067[1:])
    ]
    return {
        "counts": import_counts(db),
        "canonical_name_and_date_groups_to_review": duplicate_name_groups,
        "hadith_1067_edges": sample,
        "multiple_chain_hadiths": sum(count > 1 for count in chain_counts.values()),
        "hadiths_without_edges": sorted(references.keys() - chain_counts.keys()),
        "failures": failures,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--rawis", type=Path, default=DATA / "all_rawis.csv")
    parser.add_argument("--bukhari", type=Path, default=DATA / "Sahih al-Bukhari.csv")
    args = parser.parse_args()
    with read_only(args.database) as db:
        report = validate(db, args.rawis, args.bukhari)
        if args.baseline:
            with read_only(args.baseline) as baseline:
                old_refs = set(catalog(baseline).values())
                new_refs = set(catalog(db).values())
                report["baseline_comparison"] = {
                    "counts": import_counts(baseline),
                    "hadith_1067_edges": edges_for_1067(baseline),
                    "legacy_references_missing_from_candidate": sorted(old_refs - new_refs),
                    "source_references_recovered": sorted(new_refs - old_refs),
                    "legacy_canonical_ids_missing_from_candidate": sorted(rawis_ids(baseline) - rawis_ids(db)),
                }
    print(json.dumps(report, indent=2))
    return int(any(report["failures"].values()))


if __name__ == "__main__":
    raise SystemExit(main())

"""Compare two SQLite databases read-only. Output counts and narrator IDs, never account details."""
import argparse
import json
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path

EDITABLE = (
    "name", "arabic_name", "aliases", "biography", "parents", "tags", "grade",
    "tawthiq", "tabaqah", "region", "birth_display", "death_display", "birth_place", "death_place",
)

def connect(path):
    return closing(sqlite3.connect(path.resolve(strict=True).as_uri() + "?mode=ro", uri=True))

def collect(db):
    db.execute("PRAGMA query_only = ON")
    db.execute("BEGIN")
    tables = {name for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    def rows(sql, *required):
        return list(db.execute(sql)) if set(required) <= tables else []
    def count(table):
        return db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] if table in tables else None

    narrators = dict((row[0], row[1:]) for row in db.execute(
        f"SELECT id, {', '.join(EDITABLE)} FROM isnad_narrator WHERE id < 800000 ORDER BY id"
    ))
    hadiths = set(rows("SELECT hadith_number FROM isnad_hadith", "isnad_hadith"))
    prophet = set(rows(
        "SELECT h.hadith_number FROM isnad_transmissionedge e JOIN isnad_hadith h ON h.id=e.hadith_id WHERE e.teacher_id=1",
        "isnad_hadith", "isnad_transmissionedge",
    ))
    # Compare canonical links by hadith number and endpoints. Generated
    # placeholder IDs, edge IDs, and route indexes cannot be matched across builds.
    canonical_edges = Counter(db.execute("""
        SELECT h.hadith_number, e.student_id, e.teacher_id
        FROM isnad_transmissionedge e JOIN isnad_hadith h ON h.id=e.hadith_id
        WHERE e.student_id < 800000 AND e.teacher_id < 800000
    """))
    prophet_edges = db.execute(
        "SELECT count(*) FROM isnad_transmissionedge WHERE teacher_id = 1"
    ).fetchone()[0]
    users = dict((name, tuple(flags)) for name, *flags in rows(
        "SELECT username,is_active,is_staff,is_superuser FROM auth_user", "auth_user"
    ))
    memberships = set(rows(
        "SELECT u.username,g.name FROM auth_user_groups m JOIN auth_user u ON m.user_id=u.id JOIN auth_group g ON m.group_id=g.id",
        "auth_user", "auth_user_groups", "auth_group",
    ))
    permissions = set(rows(
        """SELECT u.username,ct.app_label,ct.model,p.codename FROM auth_user_user_permissions m
        JOIN auth_user u ON m.user_id=u.id JOIN auth_permission p ON m.permission_id=p.id
        JOIN django_content_type ct ON p.content_type_id=ct.id""",
        "auth_user", "auth_user_user_permissions", "auth_permission", "django_content_type",
    ))
    group_permissions = set(rows(
        """SELECT g.name,ct.app_label,ct.model,p.codename FROM auth_group_permissions m
        JOIN auth_group g ON m.group_id=g.id JOIN auth_permission p ON m.permission_id=p.id
        JOIN django_content_type ct ON p.content_type_id=ct.id""",
        "auth_group", "auth_group_permissions", "auth_permission", "django_content_type",
    ))
    columns = {row[1] for row in db.execute("PRAGMA table_info(isnad_transmissionedge)")}
    multi = (db.execute("""SELECT count(*) FROM (SELECT hadith_id FROM isnad_transmissionedge
            GROUP BY hadith_id HAVING count(DISTINCT chain_index)>1)""").fetchone()[0]
            if "chain_index" in columns else None)
    stats = {
        "hadiths": count("isnad_hadith"), "narrators": count("isnad_narrator"),
        "canonical_narrators": len(narrators), "edges": count("isnad_transmissionedge"),
        "prophet_edges": prophet_edges, "hadiths_with_prophet_edge": len(prophet), "multiple_indexed_routes": multi,
        "foreign_key_violations": len(list(db.execute("PRAGMA foreign_key_check"))),
        "migrations": rows("SELECT app,name FROM django_migrations ORDER BY app,name", "django_migrations"),
        "accounts": count("auth_user"), "groups": count("auth_group"),
        "staff": sum(bool(flags[1]) for flags in users.values()),
        "superusers": sum(bool(flags[2]) for flags in users.values()),
    }
    return stats, narrators, hadiths, prophet, users, memberships, permissions, group_permissions, canonical_edges

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("active", type=Path)
    parser.add_argument("corrected", type=Path)
    args = parser.parse_args()
    with connect(args.active) as active, connect(args.corrected) as candidate:
        a, b = collect(active), collect(candidate)

    def delta(old, new):
        return {"active_only": len(set(old) - set(new)), "corrected_only": len(set(new) - set(old))}
    changed = {
        i: [field for field, old, new in zip(EDITABLE, a[1][i], b[1][i]) if old != new]
        for i in sorted(a[1].keys() & b[1].keys()) if a[1][i] != b[1][i]
    }
    print(json.dumps({
        "active": a[0], "corrected": b[0],
        "canonical_ids": delta(a[1], b[1]), "hadith_numbers": delta(a[2], b[2]),
        "hadith_numbers_with_prophet_edges": delta(a[3], b[3]),
        "accounts": delta(a[4], b[4]),
        "shared_accounts_with_changed_flags": sum(a[4][u] != b[4][u] for u in a[4].keys() & b[4].keys()),
        "group_memberships": delta(a[5], b[5]), "direct_permissions": delta(a[6], b[6]),
        "group_permissions": delta(a[7], b[7]),
        "migration_records": delta(a[0]["migrations"], b[0]["migrations"]),
        "canonical_edge_occurrences": {
            "active_only": sum((a[8] - b[8]).values()),
            "corrected_only": sum((b[8] - a[8]).values()),
        },
        "profile_differences_for_review": changed,
    }, indent=2))

if __name__ == "__main__":
    main()

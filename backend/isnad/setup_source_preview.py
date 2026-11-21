"""Build a pinned read-only crosswalk and verify the Bukhari 15 preview."""
import argparse
import hashlib
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from .collection_scope import KG_BUKHARI_BOOK_ID
from .export_source_records import export_json, export_records, readonly_connection
from .source_api import MAX_BUNDLE_BYTES
from .source_crosswalk import build_crosswalk, parse_record
from .source_matching import external_key

PINNED = {
    "kg": ("hf-d5280843", "d528084321e715006712e0e2461809a3afc9408065a1d1af90238c8b723815a6"),
    "fawaz": ("cdn-v1-ar", "f887d8724f75fb6e1d5d29342a173af5346ad9b933173c85e6e3cb570063ea33"),
    "jaguar": ("v1.1.0", "09268f6384da9ae4bd1c4051c4235c2d1c350829d5c56ca82cd770c682374c8e"),
}
def check_hash(path, expected):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != expected:
        raise ValueError(f"{path}: SHA-256 {digest}; expected {expected}")


def write_new(path, data):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False)
        stream.write("\n")


def setup(args):
    for source, (_, digest) in PINNED.items():
        path = getattr(args, source)
        if path is not None:
            check_hash(path, digest)
    with closing(readonly_connection(args.visual)) as db:
        db.execute("BEGIN")
        counts = tuple(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                       for table in ("isnad_hadith", "isnad_transmissionedge"))
        if counts != (args.expected_hadiths, args.expected_edges):
            raise ValueError(f"Selected Visual database has {counts} hadiths/edges; check the file and expected counts")
        columns = {row[1] for row in db.execute("PRAGMA table_info(isnad_transmissionedge)")}
        has_index = "chain_index" in columns
        visual = export_records(db, "visual", args.visual_edition)
    with closing(readonly_connection(args.kg)) as db:
        kg = export_records(db, "kg", PINNED["kg"][0], int(KG_BUKHARI_BOOK_ID))
    sources = {"visual": visual, "kg": kg}
    for source in ("fawaz", "jaguar"):
        path = getattr(args, source)
        if path is not None:
            sources[source] = export_json(path, source, PINNED[source][0])
    left = [parse_record(row) for row in visual]
    right = [parse_record(row) for name, rows in sources.items() if name != "visual" for row in rows]
    if any(len(records) != len({external_key(row) for row in records}) for records in (left, right)):
        raise ValueError("Duplicate provider/edition/native IDs in input records")
    bundle = build_crosswalk(left, right)
    bundle["inputs"] = {
        "visual": {"edition": args.visual_edition, "hadiths": counts[0], "edges": counts[1], "chain_index_available": has_index},
        **{name: {"edition": PINNED[name][0], "sha256": PINNED[name][1]}
           for name in sources if name != "visual"},
    }
    args.output.mkdir(parents=True, exist_ok=False)
    for name, rows in sources.items():
        write_new(args.output / f"{name}.json", rows)
    # Check the exact serialized bytes before publishing the final filename.
    pending = args.output / "proposals.pending"
    write_new(pending, bundle)
    if pending.stat().st_size > MAX_BUNDLE_BYTES:
        raise ValueError("Generated crosswalk exceeds the Django manifest size limit")
    output = args.output / "proposals.json"
    pending.rename(output)
    print(json.dumps({"crosswalk": str(output.resolve()), "chain_index_available": has_index, **bundle["counts"]}))


def get_json(url):
    with urlopen(url, timeout=12) as response:
        return json.load(response)


def expect_not_found(url):
    try:
        get_json(url)
    except HTTPError as error:
        with error:
            if error.code == 404:
                return
        raise
    raise ValueError(f"Expected HTTP 404 from {url}")


def verify(args):
    os.environ["DJANGO_SETTINGS_MODULE"] = "core.settings"
    import django
    django.setup()
    from django.conf import settings

    stats = get_json(settings.HADITH_KG_API_URL.rstrip("/") + "/api/stats")
    if not isinstance(stats, dict):
        raise ValueError("Unexpected Knowledge Graph stats response")
    api = args.django_url.rstrip("/") + "/api/v1"
    kg = get_json(api + "/knowledge-graph/hadiths/14/")
    if (str(kg.get("bookId")), str(kg.get("noInBook"))) != (KG_BUKHARI_BOOK_ID, "14"):
        raise ValueError("KG ID 14 is not Bukhari 14 in the configured service")
    if {"sanads", "visual_isnad_chains"} & kg.keys():
        raise ValueError("Unreviewed KG sanads are exposed")
    expect_not_found(api + "/knowledge-graph/hadiths/17154/")
    print("PASS KG Bukhari text lookup and rejection of Abu Dawud 832")

    root = api + "/hadiths/15/"
    original = get_json(root + "?chain=1")
    if str(original.get("hadith_number")) != "15" or not isinstance(original.get("edges"), list):
        raise ValueError("Cannot verify the original Visual Isnad graph for Bukhari 15")
    print(f"PASS original graph; chain_index_available={original.get('chain_index_available')}")
    proposals = get_json(root + "sources/?page_size=400")
    if proposals.get("status") != "available":
        raise ValueError(f"Django source status: {proposals.get('status')}; restart with the generated crosswalk and correct database")
    rows = [row for row in proposals["results"] if row["provider"] == "hadith_kg" and row["right_id"] == "14"]
    if len(rows) != 1 or rows[0]["status"] != "review_required" or rows[0]["can_preview_routes"]:
        raise ValueError("Expected a single unreviewed proposal for Visual 15 to KG 14")
    endpoint = root + "source-routes/?" + urlencode({"source_key": rows[0]["right_key"]})
    expect_not_found(endpoint)
    print("PASS Bukhari 15 text proposal and rejection of unreviewed route preview")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    for name in ("visual", "kg", "fawaz", "jaguar", "output"):
        build.add_argument("--" + name, type=Path, required=name in {"visual", "kg", "output"})
    build.add_argument("--visual-edition", required=True)
    build.add_argument("--expected-hadiths", type=int, required=True)
    build.add_argument("--expected-edges", type=int, required=True)
    check = commands.add_parser("verify")
    check.add_argument("--django-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    try:
        (setup if args.command == "build" else verify)(args)
    except (OSError, sqlite3.DatabaseError, KeyError, TypeError, ValueError) as error:
        parser.exit(1, f"Source {args.command} failed: {error}\n")


if __name__ == "__main__":
    main()

"""Serve operator-supplied crosswalk proposals without changing application data."""
import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings

from .source_matching import HadithRecord, external_key, text_digest

MAX_BUNDLE_BYTES = 32 * 1024 * 1024
PROVIDERS = {"hadith_kg", "jaguar", "fawaz"}


@lru_cache(maxsize=4)
def load_proposals(path, modified, size):
    if size > MAX_BUNDLE_BYTES:
        raise ValueError("Crosswalk too large")
    with path.open(encoding="utf-8") as stream:
        bundle = json.loads(stream.read(MAX_BUNDLE_BYTES + 1))
    if bundle["schema_version"] != 2 or bundle["policy"] != "proposals_only_no_automatic_adoption":
        raise ValueError("Unsupported crosswalk")
    indexed = {}
    for row in bundle["proposals"]:
        metadata = row["provider"], row["edition"], row["right_id"]
        if row["left_provider"] != "visual_isnad" or row["provider"] not in PROVIDERS:
            continue
        if not all(isinstance(value, str) and value for value in metadata):
            raise ValueError("Invalid source identifier")
        source = HadithRecord(*metadata, "صحيح البخاري", "")
        if row["right_key"] != external_key(source):
            raise ValueError("Source key does not match provenance")
        indexed.setdefault(row["left_id"], {})[row["right_key"]] = row
    return indexed


def local_record(hadith):
    return HadithRecord(
        "visual_isnad", "", str(hadith.pk), "صحيح البخاري",
        hadith.arabic_matn, hadith.in_book_reference, hadith.arabic_full, hadith.arabic_isnad,
    )


def source_candidates(hadith):
    title = hadith.book_title.casefold()
    if "bukhari" not in title and "البخاري" not in title:
        return "not_applicable", []
    path = getattr(settings, "HADITH_SOURCE_CROSSWALK", "")
    if not path:
        return "not_configured", []
    try:
        path = Path(path)
        stat = path.stat()
        rows = load_proposals(path, stat.st_mtime_ns, stat.st_size).get(str(hadith.pk), {})
        digest = text_digest(local_record(hadith))
        candidates = [{
            **{field: row[field] for field in (
                "right_key", "right_id", "provider", "edition", "reference", "confidence",
                "evidence", "reference_equal", "reason", "ambiguity",
            )},
            "isnad_agreement": row.get("isnad_agreement", "unavailable"),
            "status": "review_required",
            "can_preview_routes": row["provider"] == "hadith_kg" and row["right_id"].isascii()
            and row["right_id"].isdecimal() and len(row["right_id"]) <= 10,
        } for row in rows.values() if row["left_text_digest"] == digest]
        return ("stale" if rows and not candidates else "available"), candidates
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return "unavailable", []

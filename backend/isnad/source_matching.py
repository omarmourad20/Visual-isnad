"""Conservative read-only matching proposals between hadith editions.

Never use a match proposal to automatically import a route.
"""
import hashlib
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import quote

MARKS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")

def normalize_arabic(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = MARKS.sub("", value)
    value = "".join(c for c in value if unicodedata.category(c) not in {"Mn", "Cf"})
    value = value.translate(str.maketrans({"أ":"ا", "إ":"ا", "آ":"ا", "ٱ":"ا", "ى":"ي"}))
    return " ".join("".join(c if c.isalnum() or c.isspace() else " " for c in value).split())

@dataclass(frozen=True)
class HadithRecord:
    provider: str
    edition: str
    native_id: str
    collection: str
    arabic_matn: str
    printed_reference: str = ""
    arabic_full: str = ""
    arabic_isnad: str = ""

@dataclass(frozen=True)
class MatchProposal:
    left_key: str
    right_key: str
    status: str
    reason: str
    normalized_text_equal: bool
    reference_equal: bool
    confidence: str
    evidence: str
    isnad_agreement: str

def external_key(record: HadithRecord) -> str:
    return ":".join(quote(part, safe="") for part in (record.provider, record.edition, record.native_id))

@lru_cache(maxsize=16_384)
def text_keys(record):
    matn, full = normalize_arabic(record.arabic_matn), normalize_arabic(record.arabic_full)
    keys = []
    if matn:
        keys.append(("matn", matn))
        if len(matn.split()) >= 8:
            keys.append(("matn_spacing", matn.replace(" ", "")))
    if full:
        keys.append(("full", full))
    return tuple(keys)


@lru_cache(maxsize=16_384)
def text_digest(record):
    material = tuple(normalize_arabic(text) for text in (record.arabic_matn, record.arabic_full, record.arabic_isnad))
    return hashlib.sha256("\0".join(material).encode("utf-8")).hexdigest()


def propose_match(left: HadithRecord, right: HadithRecord) -> MatchProposal:
    left_keys, right_keys = text_keys(left), text_keys(right)
    evidence = next((kind for kind, text in left_keys if (kind, text) in right_keys), "")
    equal_ref = bool(left.printed_reference and right.printed_reference and
                     left.printed_reference.strip() == right.printed_reference.strip())
    same_collection = bool(left.collection and right.collection and
                           normalize_arabic(left.collection) == normalize_arabic(right.collection))
    if not left_keys or not right_keys:
        status, reason, confidence = "insufficient_evidence", "Arabic text is missing", "none"
    elif not same_collection:
        status, reason, confidence = "not_matched", "Collection mismatch or unknown collection", "none"
    elif not evidence:
        status, reason, confidence = "not_matched", "No comparable normalized text agrees", "none"
    else:
        status = "review_required"
        confidence = "text_agreement" if evidence == "matn" else "limited_text_agreement"
        reason = {
            "matn": "Normalized matn agrees",
            "matn_spacing": "Matn agrees after removing word spacing",
            "full": "Normalized full report agrees",
        }[evidence] + "; verify edition, chain order, and narrator identities"
    left_isnad, right_isnad = normalize_arabic(left.arabic_isnad), normalize_arabic(right.arabic_isnad)
    isnad_agreement = "unavailable"
    if left_isnad and right_isnad:
        isnad_agreement = "text_agrees" if left_isnad == right_isnad else "text_differs"
    return MatchProposal(external_key(left), external_key(right), status, reason,
                         evidence == "matn", equal_ref, confidence, evidence, isnad_agreement)

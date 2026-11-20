"""Conservative read-only matching proposals between hadith editions.

Never use a match proposal to automatically import a route.
"""
import re
import unicodedata
from dataclasses import dataclass

MARKS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")

def normalize_arabic(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = MARKS.sub("", value)
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

@dataclass(frozen=True)
class MatchProposal:
    left_key: str
    right_key: str
    status: str
    reason: str
    normalized_text_equal: bool
    reference_equal: bool

def external_key(record: HadithRecord) -> str:
    return ":".join((record.provider, record.edition, record.native_id))

def propose_match(left: HadithRecord, right: HadithRecord) -> MatchProposal:
    ltext, rtext = normalize_arabic(left.arabic_matn), normalize_arabic(right.arabic_matn)
    equal_text = bool(ltext and rtext and ltext == rtext)
    equal_ref = bool(left.printed_reference and right.printed_reference and
                     left.printed_reference.strip() == right.printed_reference.strip())
    same_collection = bool(left.collection and right.collection and
                           normalize_arabic(left.collection) == normalize_arabic(right.collection))
    if not ltext or not rtext:
        status, reason = "insufficient_evidence", "Arabic matn is missing"
    elif not same_collection:
        status, reason = "not_matched", "Collection mismatch or unknown collection"
    elif not equal_text:
        status, reason = "not_matched", "Normalized Arabic matn differs"
    elif equal_ref:
        status, reason = "review_required", "Text and printed reference agree; verify edition and isnad"
    else:
        status, reason = "review_required", "Text agrees but printed references differ or are missing"
    return MatchProposal(external_key(left), external_key(right), status, reason,
                         equal_text, equal_ref)

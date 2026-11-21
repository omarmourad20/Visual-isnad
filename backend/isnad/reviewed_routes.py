"""Narrow read-time corrections for documented legacy import errors."""
import csv
import json
from functools import lru_cache

from rawis_catalog import DATA_DIR

from .models import Narrator
from .source_matching import normalize_arabic

SOURCE_URL = "https://sunnah.com/bukhari:15"
IBN_ULAYYA_ID = 20208
SOURCE_ISNAD = normalize_arabic(
    "حَدَّثَنَا يَعْقُوبُ بْنُ إِبْرَاهِيمَ، قَالَ حَدَّثَنَا ابْنُ عُلَيَّةَ، عَنْ عَبْدِ الْعَزِيزِ بْنِ صُهَيْبٍ، "
    "عَنْ أَنَسٍ، عَنِ النَّبِيِّ صلى الله عليه وسلم ح وَحَدَّثَنَا آدَمُ، قَالَ حَدَّثَنَا شُعْبَةُ، "
    "عَنْ قَتَادَةَ، عَنْ أَنَسٍ، قَالَ قَالَ النَّبِيُّ صلى الله عليه وسلم"
)
LEGACY_PATHS = (30001, 20184, 5888, 11295, 19, 1), (30001, 20404, 20020, 11019, 19)
LEGACY_LINKS = tuple(
    (student, teacher) for path in LEGACY_PATHS for student, teacher in zip(path, path[1:])
)
FIRST_THREE = ((30001, 30400), (30400, IBN_ULAYYA_ID), (IBN_ULAYYA_ID, 11295))


@lru_cache(maxsize=1)
def ibn_ulayya_supplement():
    try:
        with (DATA_DIR / "rawis_supplement.csv").open(encoding="utf-8-sig", newline="") as stream:
            return next((row for row in csv.DictReader(stream) if row["scholar_indx"] == str(IBN_ULAYYA_ID)), None)
    except FileNotFoundError:
        return None


def supplemental_profile(narrator_id):
    """Provide the documented profile without inserting a narrator row."""
    if str(narrator_id) != str(IBN_ULAYYA_ID):
        return None
    row = ibn_ulayya_supplement()
    if row is None:
        return None
    english, arabic = row["name"].rsplit(" (", 1)
    return Narrator(
        id=IBN_ULAYYA_ID, name=english, arabic_name=arabic.removesuffix(")"),
        aliases=row["aliases_arabic"], grade=row["grade"],
        birth_year=int(row["birth_date_hijri"]), death_year=int(row["death_date_hijri"]),
        teachers_inds=row["teachers_inds"], students_inds=row["students_inds"],
    )


def correct_legacy_bukhari_15(hadith, edges):
    """Apply the reviewed identities only when source and legacy graph both match."""
    if (
        hadith.reference_url != SOURCE_URL
        or normalize_arabic(hadith.arabic_isnad) != SOURCE_ISNAD
        or tuple((edge["student"], edge["teacher"]) for edge in edges) != LEGACY_LINKS
        or any(edge["chain_index"] is not None for edge in edges)
        or [edge["sequence"] for edge in edges] != list(range(len(LEGACY_LINKS)))
        or ibn_ulayya_supplement() is None
    ):
        return edges
    return [
        {
            **edge, "student": student, "teacher": teacher,
            "correction": {
                "source_url": SOURCE_URL,
                "evidence": "Source isnad, vocalized commentary row 14, and narrator catalog supplement",
                "original_student": edge["student"], "original_teacher": edge["teacher"],
            },
        }
        for edge, (student, teacher) in zip(edges[:3], FIRST_THREE)
    ] + list(edges[3:])

@lru_cache(maxsize=1)
def reviewed_narrator_routes():
    path = DATA_DIR / "reviewed_legacy_narrator_routes.json"
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except FileNotFoundError:
        return {}


def correct_reviewed_legacy_route(hadith, edges):
    if hadith.reference_url == SOURCE_URL:
        return correct_legacy_bukhari_15(hadith, edges)
    review = reviewed_narrator_routes().get(hadith.reference_url)
    if (
        review is None
        or any(edge["chain_index"] is not None for edge in edges)
        or [[edge["sequence"], edge["student"], edge["teacher"]] for edge in edges] != review["edges"]
        or normalize_arabic(hadith.arabic_isnad) != normalize_arabic(review["isnad"])
        or ibn_ulayya_supplement() is None
    ):
        return edges
    replacements = {int(key): value for key, value in review["replacements"].items()}
    display = []
    for edge in edges:
        student, teacher = edge["student"], edge["teacher"]
        corrected = replacements.get(student, student), replacements.get(teacher, teacher)
        if corrected == (student, teacher):
            display.append(edge)
        else:
            display.append({
                **edge, "student": corrected[0], "teacher": corrected[1],
                "correction": {
                    "source_url": hadith.reference_url, "evidence": review["evidence"],
                    "original_student": student, "original_teacher": teacher,
                },
            })
    return display

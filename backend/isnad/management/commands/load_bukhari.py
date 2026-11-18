import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from isnad.models import Hadith, Narrator, TransmissionEdge
from isnad.scholar_bios import load_cache
from rawis_catalog import DATA_DIR, UNRESOLVED_NARRATOR_ID_START, read_rawis

INVISIBLE = dict.fromkeys(map(ord, "\u200f\u200e\u200c\u200d\u200b"), None)
TASHKEEL_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
SPACE_RE = re.compile(r"\s+")
HONORIFIC_RE = re.compile(
    r"رضي الله عن\S*|رضى الله عن\S*|صل[ىي] الله عليه وسلم|عليه السلام|صلعم"
)
PARENT_ID_RE = re.compile(r"\[(\d+)\]")
YEAR_RE = re.compile(r"(\d+)\s*(BH|AH)", re.I)
HADITH_NO_RE = re.compile(r"bukhari:(\d+[a-z]?(?:-\d+)?)(?:$|[/?#])", re.I)
BOOK_REF_RE = re.compile(r"Book\s+(\d+)", re.I)
GENERATION_RE = re.compile(r"\[([^\]]*(?:generation|century)[^\]]*)\]", re.I)

FATHER_KEYS = {"ابو", "ابيه", "ابوه", "ابيها", "اباها"}
PROPHET_KEYS = {"رسول الله", "النبي", "نبي الله", "رسول الله صلى الله عليه وسلم"}
BUKHARI_ID = 30001
PROPHET_ID = 1
UNMATCHED_ID_START = UNRESOLVED_NARRATOR_ID_START

COMPILER_TERMS = {"حدثنا", "حدثني", "اخبرنا", "اخبرني", "انبانا", "انباني", "سمعت", "سمعنا", "قال لنا", "قال لي"}
TERMS = COMPILER_TERMS | {"عن", "انه سمع", "انها سمعت", "اخبرتني", "حدثتني"}
TERM_SPLIT_RE = re.compile(r"\bو?(" + "|".join(sorted(TERMS)) + r")\s+")
SKIP_NAME_KEYS = {"هرقل", "جبريل", "الملك", "و", "ح"}
TAHWIL_RE = re.compile(r"(?<!\w)ح[\u064b-\u065f]*(?![\w\u064b-\u065f])")
PROPHET_TITLE = r"(?:النبي|رسول الله|نبي الله)"
PROPHET_TITLE_RE = re.compile(rf"^{PROPHET_TITLE}\b")
PROPHET_REPORT_RE = re.compile(rf"^{PROPHET_TITLE}(?:$|\s+(?:قال|يقول)\b)")
PROPHET_ATTRIBUTION_RE = re.compile(
    rf"\s+(?:(?:انه قال|انها قالت|قالت)\s+)(?=(?:قال\s+)?{PROPHET_TITLE}\b)"
)
DIRECT_REPORT_TERMS = {"عن", "سمعت", "سمعنا", "انه سمع", "انها سمعت", "حدثني", "حدثنا", "اخبرني", "اخبرنا"}


def clean_text(value: str) -> str:
    if not value:
        return ""
    value = str(value).translate(INVISIBLE)
    return SPACE_RE.sub(" ", value).strip()


def normalize_arabic(value: str) -> str:
    if not value:
        return ""
    text = TASHKEEL_RE.sub("", clean_text(value))
    text = (
        text.replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ة", "ه")
        .replace("ى", "ي")
        .replace("ؤ", "و")
        .replace("ئ", "ي")
        .replace("\u06cc", "ي")
        .replace("\u06d2", "ي")
        .replace("\u06a9", "ك")
        .replace("\u06c1", "ه")
        .replace("\u06be", "ه")
        .replace("ه", "ه")
    )
    text = HONORIFIC_RE.sub(" ", text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return SPACE_RE.sub(" ", text).strip()


def extract_arabic_span(raw_name: str) -> str:
    spans = re.findall(r"[\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)*", str(raw_name))
    if not spans:
        return ""
    arabic = max(spans, key=len)
    return HONORIFIC_RE.sub(" ", arabic).strip()


def extract_english_name(raw_name: str) -> str:
    english = re.sub(r"[\u0600-\u06FF]+", " ", str(raw_name))
    english = re.sub(r"\([^)]*\)", " ", english)
    english = clean_text(english).replace("(saw)", "")
    english = re.sub(r"[()]+", " ", english)
    return SPACE_RE.sub(" ", english).strip(" -_,")[:255]


def parse_int(value):
    if value in (None, "", "NA", "N/A"):
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def hijri_display(date_blob: str, hijri_num, default_era: str) -> str:
    if not hijri_num:
        return ""
    blob = date_blob or ""
    match = YEAR_RE.search(blob)
    if match:
        return f"{match.group(1)} {match.group(2).upper()}"
    return f"{hijri_num} {default_era}"


def parse_id_list(value: str) -> list[int]:
    if not value or value.strip() in {"NA", "N/A"}:
        return []
    ids = []
    seen = set()
    for part in value.split(","):
        part = part.strip()
        if not part or part in {"NA", "N/A"}:
            continue
        try:
            number = int(part)
        except ValueError:
            continue
        if number not in seen:
            ids.append(number)
            seen.add(number)
    return ids


def split_isnad_matn(arabic_text: str) -> tuple[str, str]:
    text = clean_text(arabic_text)
    if not text:
        return "", ""

    narrative = re.search(
        r"(?:قَالَ\s+)?(?:قَرَأَ|سَجَدَ)\s+النَّبِيّ[َُ]"
        r"|أَنَّ\s+النَّبِيَّ\s+(?:صلى الله عليه وسلم\s+)?(?:قَرَأَ|سَجَدَ)",
        text,
    )
    cuts = [idx for quote in ('"', "«", "\u201c") if (idx := text.find(quote, 26)) != -1]
    if narrative and narrative.start() > 20:
        cuts.append(narrative.start())
    if cuts:
        idx = min(cuts)
        return text[:idx].strip(" ،,:"), text[idx:].strip()

    story_cut = re.search(
        r"(أَنَّ هِرَقْل|ان هرقل|فِي قَوْلِهِ تَعَالَى|في قوله تعالى|أَنَّهَا قَالَتْ|انها قالت|سَأَلَ رَسُولَ|سال رسول)",
        text,
    )
    if story_cut and story_cut.start() > 20:
        return text[: story_cut.start()].strip(" ،,:"), text[story_cut.start() :].strip()

    vocalized = re.search(
        r"صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ(?:\s*[،,]?\s*(?:يَقُولُ|فَقَالَ|قَالَ))?",
        text,
    )
    if vocalized and vocalized.end() < len(text) - 8:
        isnad = text[: vocalized.end()].strip(" ،,:")
        matn = text[vocalized.end() :].strip(" :،,")
        matn = re.sub(r"^(يَقُولُ|فَقَالَ|قَالَ)\s*", "", matn)
        return isnad, matn
    return text, ""


def _clean_person_name(name: str) -> str:
    name = name.strip(" ،,:ـ-")
    name = re.sub(r"^(و|قال|قالت|يقول)\s+", "", name)
    name = re.sub(r"\s+(قال|قالت|يقول|نحو[ه]|مثله|بهذا)$", "", name)
    name = re.sub(r"\s+(على المنبر|علي المنبر)$", "", name)
    name = re.sub(r"\s+اخبره$", "", name)
    name = re.sub(r"ـ+", " ", name)
    return SPACE_RE.sub(" ", name).strip()


def _looks_like_name(name: str) -> bool:
    if not name or name in SKIP_NAME_KEYS:
        return False
    if re.search(r"سال |هرقل|في قوله|يحدث|فقال|كنت|قلت ", name):
        return False
    tokens = name.split()
    if len(tokens) > 9:
        return False
    markers = ("بن", "ابن", "ابي", "ابو", "ابا", "بنت", "ام")
    return any(token in markers or name.startswith(token) for token in tokens) or len(tokens) <= 4


def _names_from_segment(segment: str, term: str) -> list[tuple[str, str]]:
    segment = _clean_person_name(segment)
    if not segment:
        return []
    if re.match(r"^(في قوله|انها قالت|انه قال)", segment):
        return []

    # An explicit transmission token supplies the relation even when the
    # title is followed by the opening words of the report.
    if term in DIRECT_REPORT_TERMS and PROPHET_TITLE_RE.match(segment):
        return [("رسول الله", term)]

    segment = PROPHET_ATTRIBUTION_RE.sub(" قال ", segment)
    segment = re.split(
        r"\s+(انها قالت|انه قال|في قوله تعالى|في قوله)\b",
        segment,
        maxsplit=1,
    )[0]
    names: list[tuple[str, str]] = []
    current_term = term
    clauses = re.split(r"\s+ان\s+", segment)
    for index, clause in enumerate(clauses):
        clause = _clean_person_name(clause)
        if re.search(r"\b(سال|هرقل|في قوله)\b", clause):
            break

        clause = re.sub(r"\s+زوج(?:ه)? (?:النبي|رسول الله)\b", "", clause)
        person, separator, report = clause.partition(" قال ")
        report = re.sub(r"^قال\s+", "", report)
        prophet_in_clause = PROPHET_REPORT_RE.match(clause) or (
            separator and PROPHET_REPORT_RE.match(report)
        )
        if PROPHET_REPORT_RE.match(person):
            person = ""
        person = _clean_person_name(re.sub(r"(قال|قالت)+$", "", person))
        if person and _looks_like_name(person):
            names.append((person, current_term if index == 0 else "ان"))
            current_term = "عن"
        elif person and index == 0 and 0 < len(person.split()) <= 6:
            names.append((person, current_term))
            current_term = "عن"
        elif index > 0 and not _looks_like_name(clause):
            break

        if prophet_in_clause:
            names.append(("رسول الله", "قال" if separator or index else current_term))
            break
        if not _looks_like_name(clause) and index > 0:
            break
    return names


def extract_chains(isnad: str) -> list[list[tuple[str, str]]]:
    """Return chains of (name, terminology) from an isnad string."""
    text = HONORIFIC_RE.sub(" ", clean_text(isnad))
    text = TASHKEEL_RE.sub("", re.sub(r"ًا|اً", "", text))
    text = re.sub(r"على المنبر", " ", text)
    chunks = [chunk.strip() for chunk in TAHWIL_RE.split(text) if chunk and chunk.strip()]
    if not chunks:
        chunks = [text]

    chains: list[list[tuple[str, str]]] = []
    for chunk in chunks:
        normalized = normalize_arabic(chunk)
        # Leading speech or a suspended "on the authority of" clause does
        # not establish a transmission from the compiler.
        normalized = re.sub(r"^(?:و?قال\s+(?!(?:لنا|لي)\b))+", "", normalized)
        pieces = TERM_SPLIT_RE.split(normalized)
        current: list[tuple[str, str]] = []
        pending_term = "قال"
        if pieces[0].strip():
            lead = _clean_person_name(pieces[0])
            if (
                len(pieces) < 3
                or not _looks_like_name(lead)
                or PROPHET_REPORT_RE.match(lead)
                or re.search(r"\b(?:ثم|علي|كنت|فدخلت|فقال|رسول الله|النبي)\b", lead)
            ):
                continue
        for piece in pieces:
            if not piece:
                continue
            if piece in TERMS:
                pending_term = piece
                continue
            # A question such as "did you hear..." and a narrative dispute
            # introduce embedded dialogue, outside this explicit route.
            boundary = re.search(r"\bانه تماري\b|\bهل\s*$", piece)
            if boundary:
                current.extend(_names_from_segment(piece[:boundary.start()], pending_term))
                break
            extracted = _names_from_segment(piece, pending_term)
            if not extracted:
                if re.search(r"في قوله|انها قالت|انه قال", piece):
                    break
                continue
            current.extend(extracted)
            if extracted[-1][0] in PROPHET_KEYS:
                break
            pending_term = "عن"
        cleaned: list[tuple[str, str]] = []
        for name, used_term in current:
            if name in PROPHET_KEYS:
                name = "رسول الله"
            if cleaned and cleaned[-1][0] == name:
                continue
            cleaned.append((name, used_term))
        if cleaned:
            chains.append(cleaned)
    return chains


def name_key(name: str) -> str:
    name = normalize_arabic(name.replace("ـ", ""))
    name = re.sub(r"\bام المومنين\b", " ", name)
    name = re.sub(r"\bعبدالله\b", "عبد الله", name)
    return " ".join(
        {"ابن": "بن", "ابي": "ابو", "ابا": "ابو"}.get(word, word)
        for word in name.split()
    )


def signed_hijri(year, display):
    if year is None:
        return None
    return -abs(year) if " BH" in display.upper() else year


class ChainMatcher:
    """Score complete chains using name evidence and documented adjacent links."""

    LINK_SCORE = 3
    FATHER_SCORE = 6
    UNMATCHED_SCORE = 1
    MIN_MARGIN = 2

    def __init__(self, narrators):
        self.names = defaultdict(dict)
        self.teachers = defaultdict(dict)
        self.students = defaultdict(dict)
        self.fathers = {}
        self.children = defaultdict(dict)
        self.dates = {}
        self.generations = {}
        self.prophet = PROPHET_ID if PROPHET_ID in narrators else None
        self.collector = BUKHARI_ID if BUKHARI_ID in narrators else None

        for narrator_id, narrator in narrators.items():
            raw_name, *documented_aliases = narrator.aliases.split(" | ")
            raw_arabic = re.findall(
                r"[\u0621-\u06ff]+(?:\s+[\u0621-\u06ff]+)*",
                HONORIFIC_RE.sub(" ", raw_name),
            )
            names = {narrator.arabic_name, narrator.name, *raw_arabic}
            birth = signed_hijri(narrator.birth_year, narrator.birth_display)
            death = signed_hijri(narrator.death_year, narrator.death_display)
            if birth is not None and death is not None and birth > death:
                birth = death = None
            self.dates[narrator_id] = (birth, death)
            generation = re.search(r"(\d+)(?:st|nd|rd|th) generation", narrator.grade, re.I)
            if generation:
                self.generations[narrator_id] = int(generation.group(1))
            for name in names:
                self.index_name(narrator_id, name_key(name))
            for alias in documented_aliases:
                # A documented kunya is evidence as a whole; a word pulled
                # from it can be another person's given name.
                key = name_key(alias)
                if key:
                    score = self.exact_name_score(key.split())
                    posting = self.names[key]
                    posting[narrator_id] = max(score, posting.get(narrator_id, 0))

            for teacher_id in parse_id_list(narrator.teachers_inds):
                if teacher_id in narrators:
                    self.add_link(narrator_id, teacher_id)
            for student_id in parse_id_list(narrator.students_inds):
                if student_id in narrators:
                    self.add_link(student_id, narrator_id)

            # In all_rawis the father is listed before the slash, then the mother.
            father = narrator.parents.partition("/")[0]
            ids = PARENT_ID_RE.findall(father)
            if len(ids) == 1 and int(ids[0]) in narrators:
                father_id = int(ids[0])
                self.fathers[narrator_id] = father_id
                self.children[father_id][narrator_id] = self.FATHER_SCORE

    def add_link(self, student_id, teacher_id):
        # A link can appear in either list. Agreement gives it more weight.
        score = self.teachers[student_id].get(teacher_id, 0) + self.LINK_SCORE
        self.teachers[student_id][teacher_id] = score
        self.students[teacher_id][student_id] = score

    @staticmethod
    def exact_name_score(words):
        substantive = len(words) - int(words[0] in {"ابو", "ام", "عبد", "بن"})
        return 12 if substantive > 1 else 3

    def index_name(self, narrator_id, full_name):
        words = full_name.split()
        for start in range(len(words)):
            for end in range(start + 1, len(words) + 1):
                span = words[start:end]
                if span[-1] in {"عبد", "بن", "بنت", "ابو", "ام"}:
                    continue
                key = " ".join(span)
                substantive = len(span) - int(span[0] in {"ابو", "ام", "عبد", "بن"})
                if key == full_name:
                    score = self.exact_name_score(span)
                elif start == 0:
                    score = 9 if substantive > 1 else 2
                else:
                    # Interior phrases can be nicknames or part of a genealogy.
                    # Require a neighboring link before trusting them.
                    score = 0
                variants = {key: score}
                if len(span) == 2 and span[0] == "بن" and span[1].startswith("ال"):
                    variants[f"بن {span[1][2:]}"] = score
                if start == 0 and substantive > 1 and end < len(words):
                    # Some source spellings put the nisba before the given name.
                    title = words[-1]
                    if title.startswith("ال"):
                        variants[f"{title} {key}"] = score
                        variants[f"{key} {title}"] = score
                for variant, weight in variants.items():
                    posting = self.names[variant]
                    posting[narrator_id] = max(weight, posting.get(narrator_id, 0))

    def candidates(self, key, previous):
        scores = {None: self.UNMATCHED_SCORE}
        if key in PROPHET_KEYS and self.prophet is not None:
            scores[self.prophet] = 12
        elif key in FATHER_KEYS:
            scores.update({self.fathers[sid]: 3 for sid in previous if sid in self.fathers})
        else:
            scores.update(self.names.get(key, {}))
            stem, _, tail = key.rpartition(" ")
            if len(stem.split()) >= 3 and tail.startswith("ال"):
                # A missing nisba in the catalog is useful only with a link.
                for sid, score in self.names.get(stem, {}).items():
                    if score >= 9:
                        scores.setdefault(sid, 0)
        return scores

    def chronology_score(self, student, teacher):
        if student is None or teacher is None:
            return 0
        student_birth, student_death = self.dates.get(student, (None, None))
        teacher_birth, teacher_death = self.dates.get(teacher, (None, None))
        if (
            student_birth is not None and teacher_death is not None and student_birth > teacher_death
            or teacher_birth is not None and student_death is not None and teacher_birth > student_death
        ):
            return float("-inf")
        student_generation = self.generations.get(student)
        teacher_generation = self.generations.get(teacher)
        if student_generation and teacher_generation and teacher_generation > student_generation + 1:
            return -1
        return 0

    def advance(self, scores, previous, relatives, father=False, backward=False):
        # Missing links are common in the biographical data. A known link is a
        # bonus, while a father reference requires an explicit matching father.
        highest = sorted(previous, key=previous.get, reverse=True)
        result = {}
        for narrator_id, score in scores.items():
            best = float("-inf")
            def compatibility(other):
                if backward:
                    return self.chronology_score(narrator_id, other)
                return self.chronology_score(other, narrator_id)

            if not father or (narrator_id is None and not backward):
                for sid in highest:
                    # A chronology adjustment is never positive. Link bonuses
                    # are evaluated separately below, including after this cutoff.
                    if previous[sid] <= best:
                        break
                    if sid != narrator_id or sid is None:
                        best = max(best, previous[sid] + compatibility(sid))
            if father and backward:
                best = max(best, previous.get(None, float("-inf")))
            for relative, link_score in relatives.get(narrator_id, {}).items():
                if relative != narrator_id and relative in previous:
                    best = max(best, previous[relative] + link_score + compatibility(relative))
            result[narrator_id] = score + best
        return result

    def complete_shared_tails(self, chains):
        if len(chains) < 2:
            return chains
        resolved = [self.resolve(chain) for chain in chains]
        last = len(chains) - 1
        completed = list(chains)
        for index in range(last - 1, -1, -1):
            endpoint = resolved[index][-1][0]
            if endpoint is None:
                continue
            # The switch marker provides the alternate route. Extend it only
            # when its endpoint occurs exactly once in the next known route.
            joins = [
                offset for offset, (narrator_id, _) in enumerate(resolved[index + 1])
                if narrator_id == endpoint
            ]
            if len(joins) == 1:
                completed[index] = chains[index] + completed[index + 1][joins[0] + 1:]
                resolved[index] = self.resolve(completed[index])
        return completed

    def resolve(self, chain, audit=None):
        # Prefix and suffix scores give the best complete path through each
        # candidate. Equal or nearly equal paths leave that position unresolved.
        keys = [name_key(name) for name, _ in chain]
        layers = []
        collector = self.collector if chain and chain[0][1] in COMPILER_TERMS else None
        forward = [{collector: 0}]
        for key in keys:
            father = key in FATHER_KEYS
            scores = self.candidates(key, forward[-1])
            layers.append(scores)
            predecessors = self.children if father else self.students
            forward.append(self.advance(scores, forward[-1], predecessors, father))

        backward = {narrator_id: 0 for narrator_id in layers[-1]} if layers else {}
        resolved = []
        margins = []
        for index in range(len(layers) - 1, -1, -1):
            totals = {
                narrator_id: prefix + backward[narrator_id]
                for narrator_id, prefix in forward[index + 1].items()
            }
            best = sorted(totals, key=totals.get, reverse=True)[:2]
            winner = best[0]
            margin = totals[winner] - totals[best[1]] if len(best) > 1 else None
            if margin is not None and margin < self.MIN_MARGIN:
                winner = None
            resolved.append(winner)
            margins.append(margin)
            if index:
                father = keys[index] in FATHER_KEYS
                scores = {sid: score + backward[sid] for sid, score in layers[index].items()}
                successors = self.teachers
                if father:
                    successors = {
                        sid: {self.fathers[sid]: self.FATHER_SCORE}
                        for sid in layers[index - 1]
                        if sid in self.fathers
                    }
                backward = self.advance(
                    dict.fromkeys(layers[index - 1], 0),
                    scores,
                    successors,
                    father,
                    backward=True,
                )

        result = []
        student_id = collector
        seen = {collector}
        for key, layer, narrator_id, margin in zip(
            keys, layers, reversed(resolved), reversed(margins), strict=True
        ):
            father = key in FATHER_KEYS
            if father and (student_id is None or self.fathers.get(student_id) != narrator_id):
                narrator_id = None
            if narrator_id is not None:
                if narrator_id in seen:
                    if audit is not None:
                        audit["repeated identity left unresolved"] += 1
                    narrator_id = None
                else:
                    seen.add(narrator_id)
            linked = narrator_id is not None and (
                father or narrator_id in self.teachers.get(student_id, ())
            )
            result.append((narrator_id, linked))
            if audit is not None:
                if narrator_id is None:
                    audit["unresolved"] += 1
                    if not father and len(layer) > 1 and margin is not None and margin < self.MIN_MARGIN:
                        audit["insufficient score margin"] += 1
                elif margin is None or margin == float("inf"):
                    audit["no viable alternative"] += 1
                elif margin >= 6:
                    audit["margin 6 or more"] += 1
                else:
                    audit["margin 2 through 5"] += 1
            student_id = narrator_id
        return result


class Command(BaseCommand):
    help = "Import all_rawis.csv and Sahih al-Bukhari.csv into a fresh migrated database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--rawis",
            default=str(DATA_DIR / "all_rawis.csv"),
            help="Path to all_rawis.csv",
        )
        parser.add_argument(
            "--bukhari",
            default=str(DATA_DIR / "Sahih al-Bukhari.csv"),
            help="Path to Sahih al-Bukhari.csv",
        )
        parser.add_argument("--limit", type=int, default=0, help="Load only the first N hadiths.")
        parser.add_argument("--report", type=Path, help="Write a JSON import report to a new file.")

    def handle(self, *args, **options):
        rawis_path = Path(options["rawis"])
        bukhari_path = Path(options["bukhari"])
        if not rawis_path.exists():
            raise CommandError(f"Rawis CSV not found: {rawis_path}")
        if not bukhari_path.exists():
            raise CommandError(f"Bukhari CSV not found: {bukhari_path}")

        if options["limit"] < 0:
            raise CommandError("--limit must be zero or positive.")
        report_path = options["report"]
        if report_path and report_path.exists():
            raise CommandError(f"Report already exists: {report_path}")

        with transaction.atomic():
            if Narrator.objects.exists() or Hadith.objects.exists() or TransmissionEdge.objects.exists():
                raise CommandError("The isnad tables must be empty. Use a separate migrated database.")
            biographies = load_cache() if rawis_path.resolve() == (DATA_DIR / "all_rawis.csv").resolve() else {}
            narrators = self.load_rawis(rawis_path, biographies)
            stats = self.load_hadiths(bukhari_path, narrators, limit=options["limit"])
            stats["cached_biographies"] = sum(bool(biographies.get(str(sid))) for sid in narrators)

        if report_path:
            with report_path.open("x", encoding="utf-8") as report:
                json.dump(stats, report, ensure_ascii=False, indent=2)
                report.write("\n")
        self.stdout.write(
            self.style.SUCCESS(
                "Loaded "
                f"{stats['hadiths']} hadiths, "
                f"{stats['edges']} edges, "
                f"{stats['matched']} matched names, "
                f"{stats['unmatched']} unmatched names, "
                f"{stats['teacher_hits']} teacher-constrained matches."
            )
        )

    def load_rawis(self, path: Path, biographies=None):
        biographies = biographies or {}
        by_id: dict[int, Narrator] = {}

        for source, row in read_rawis(path):
            scholar_id = parse_int(row.get("scholar_indx"))
            if scholar_id is None or not 0 < scholar_id < UNMATCHED_ID_START:
                raise CommandError(f"Invalid narrator ID in {source.name}.")
            if scholar_id in by_id:
                raise CommandError(f"Duplicate narrator ID {scholar_id} in {source.name}.")
            raw_name = row.get("name") or ""
            english = extract_english_name(raw_name) or raw_name[:255]
            arabic = extract_arabic_span(raw_name)
            birth_year = parse_int(row.get("birth_date_hijri"))
            death_year = parse_int(row.get("death_date_hijri"))
            grade = (row.get("grade") or "")[:255]
            generation = ""
            gen_match = GENERATION_RE.search(grade)
            if gen_match:
                generation = gen_match.group(1)[:255]

            narrator = Narrator(
                id=scholar_id,
                name=english,
                arabic_name=arabic[:255],
                aliases=" | ".join(filter(None, (raw_name, row.get("aliases_arabic")))),
                birth_year=birth_year,
                death_year=death_year,
                birth_display=hijri_display(row.get("birth_date") or "", birth_year, "BH" if birth_year and "BH" in (row.get("birth_date_place") or "") else "AH"),
                death_display=hijri_display(row.get("death_date") or row.get("death_date_place") or "", death_year, "AH"),
                birth_place=(row.get("birth_place") or "")[:255],
                death_place=(row.get("death_place") or "")[:255],
                tabaqah=generation or grade[:255],
                region=(row.get("places_of_stay") or "")[:255],
                tawthiq=grade[:255],
                grade=grade,
                tags=row.get("tags") or "",
                biography=biographies.get(str(scholar_id)) or row.get("area_of_interest") or "",
                parents=row.get("parents") or "",
                teachers_inds=row.get("teachers_inds") or "",
                students_inds=row.get("students_inds") or "",
            )
            by_id[scholar_id] = narrator

        Narrator.objects.bulk_create(list(by_id.values()), batch_size=1000)
        return by_id

    def load_hadiths(self, path, narrators, limit=0):
        unmatched_id = UNMATCHED_ID_START
        unresolved_names = Counter()
        confidence = Counter()
        canonical_count = len(narrators)
        if BUKHARI_ID not in narrators:
            raise CommandError("The rawis CSV is missing the compiler ID 30001.")
        hadiths: list[Hadith] = []
        parsed_chains: list[list[list[tuple[str, str]]]] = []
        matched = unmatched = teacher_hits = 0

        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if limit:
            rows = rows[:limit]

        references = []
        seen = set()
        for row in rows:
            reference = (row.get("Reference") or "").strip()
            number_match = HADITH_NO_RE.search(reference)
            if not number_match:
                raise CommandError(f"Invalid Bukhari reference: {reference!r}.")
            number = number_match.group(1).lower()
            if number in seen:
                raise CommandError(f"Duplicate Bukhari reference: {number}.")
            seen.add(number)
            references.append(number)

        next_id = max((int(number) for number in references if number.isdecimal()), default=0) + 1
        for row, hadith_number in zip(rows, references, strict=True):
            arabic_full = clean_text(row.get("Arabic_Text") or "")
            isnad, matn = split_isnad_matn(arabic_full)
            if not matn:
                # If the quote-based split failed, still try to keep a usable matn
                # by cutting at the first explicit prophetic formula.
                vocalized = re.search(
                    r"صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ\s*(?:يَقُولُ|فَقَالَ)?\s*",
                    arabic_full,
                )
                if vocalized and vocalized.end() < len(arabic_full) - 10:
                    isnad = arabic_full[: vocalized.end()].strip(" ،,:")
                    matn = arabic_full[vocalized.end() :].strip(" :،,")
            chains = extract_chains(isnad)
            parsed_chains.append(chains)

            reference = row.get("Reference") or ""
            chapter_en = (row.get("Chapter_Title_English") or "")[:255]
            numeric_id = parse_int(hadith_number)
            if numeric_id is None:
                numeric_id = next_id
                next_id += 1
            in_book_reference = (row.get("In-book reference") or "")[:100]
            book_match = BOOK_REF_RE.search(in_book_reference)
            hadiths.append(
                Hadith(
                    id=numeric_id,
                    hadith_number=str(hadith_number)[:50],
                    book_number=int(book_match.group(1)) if book_match else None,
                    in_book_reference=in_book_reference,
                    book_title=(row.get("Book") or "Sahih al-Bukhari")[:255],
                    chapter_number=(row.get("Chapter_Number") or "")[:50],
                    chapter_title=chapter_en,
                    chapter_title_arabic=(row.get("Chapter_Title_Arabic") or "")[:255],
                    arabic_isnad=isnad,
                    arabic_matn=matn or arabic_full,
                    arabic_full=arabic_full,
                    english_matn=clean_text(row.get("English_Text") or ""),
                    topic=chapter_en,
                    reference_url=reference[:200],
                    grade=(row.get("Grade") or "")[:100],
                )
            )

        Hadith.objects.bulk_create(hadiths, batch_size=500)

        edges: list[TransmissionEdge] = []
        new_unmatched: list[Narrator] = []

        def get_or_make_unmatched(name: str) -> Narrator:
            nonlocal unmatched_id
            unresolved_names[name_key(name)] += 1
            narrator = Narrator(
                id=unmatched_id,
                name=name[:255],
                arabic_name=name[:255],
                aliases=name,
                tabaqah="",
                region="",
                tawthiq="",
                grade="Unmatched isnad name",
                biography="Extracted from a Bukhari isnad; no confident all_rawis match.",
            )
            unmatched_id += 1
            new_unmatched.append(narrator)
            return narrator

        matcher = ChainMatcher(narrators)
        bukhari = narrators.get(BUKHARI_ID)

        for hadith, chains in zip(hadiths, parsed_chains, strict=True):
            sequence = 0
            for chain_index, chain in enumerate(
                chain for chain in matcher.complete_shared_tails(chains)
                if len(chain) > 1 or chain[0][1] in COMPILER_TERMS
            ):
                student = bukhari if chain[0][1] in COMPILER_TERMS else None
                for (name, term), (narrator_id, linked) in zip(chain, matcher.resolve(chain, confidence), strict=True):
                    matched_narrator = narrators.get(narrator_id)
                    if matched_narrator is None:
                        matched_narrator = get_or_make_unmatched(name)
                        unmatched += 1
                    else:
                        matched += 1
                        if linked:
                            teacher_hits += 1
                    if student is not None and matched_narrator.id != student.id:
                        edges.append(
                            TransmissionEdge(
                                teacher=matched_narrator,
                                student=student,
                                hadith=hadith,
                                terminology=term[:100],
                                sequence=sequence,
                                chain_index=chain_index,
                            )
                        )
                        sequence += 1
                    student = matched_narrator
        if new_unmatched:
            Narrator.objects.bulk_create(new_unmatched, batch_size=500)

        TransmissionEdge.objects.bulk_create(edges, batch_size=1000)
        persisted_chains = defaultdict(set)
        for edge in edges:
            persisted_chains[edge.hadith_id].add(edge.chain_index)
        return {
            "hadiths": len(hadiths),
            "edges": len(edges),
            "matched": matched,
            "unmatched": unmatched,
            "teacher_hits": teacher_hits,
            "canonical_narrators": canonical_count,
            "chains": sum(map(len, persisted_chains.values())),
            "multiple_chain_hadiths": sum(len(indices) > 1 for indices in persisted_chains.values()),
            "hadiths_without_extracted_chain": [
                hadith.hadith_number
                for hadith in hadiths
                if hadith.id not in persisted_chains
            ],
            "confidence": dict(confidence),
            "unresolved_names": dict(unresolved_names.most_common()),
        }

import csv
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from isnad.management.commands.load_bukhari import (
    BUKHARI_ID,
    DATA_DIR,
    ChainMatcher,
    Command,
    extract_chains,
    split_isnad_matn,
)
from isnad.models import Hadith, Narrator, TransmissionEdge


class BukhariMatchingTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with patch.object(Narrator.objects, "bulk_create"):
            cls.matcher = ChainMatcher(Command().load_rawis(DATA_DIR / "all_rawis.csv"))
        expected = {
            1: [30418, 20005, 11062, 11213, 11042, 3, 1],
            2: [30355, 20001, 11065, 10511, 53],
            3: [30399, 20023, 11207, 11013, 10511, 53],
            1067: [30160, 20278, 20020, 11049, 11054, 16],
            1070: [30329, 20020, 11049, 11054, 16],
            1071: [30175, 20258, 11015, 11023, 17],
            4862: [30350, 20258, 11015, 11023, 17],
            7563: [30290, 20356, 11379, 11406, 13, 1],
        }
        cls.expected = expected
        with (DATA_DIR / "Sahih al-Bukhari.csv").open(encoding="utf-8-sig", newline="") as source:
            cls.texts = {
                int(number): row["Arabic_Text"]
                for row in csv.DictReader(source)
                if (number := row["Reference"].rsplit(":", 1)[-1]).isdigit()
                and int(number) in expected
            }

    def test_known_chains(self):
        for number, expected_ids in self.expected.items():
            with self.subTest(hadith=number):
                isnad, _ = split_isnad_matn(self.texts[number])
                chain, = extract_chains(isnad)
                actual_ids = [narrator_id for narrator_id, _ in self.matcher.resolve(chain)]
                self.assertEqual(actual_ids, expected_ids)

    def test_recitation_opens_the_matn_in_1067(self):
        _, matn = split_isnad_matn(self.texts[1067])
        self.assertTrue(matn.startswith("قَالَ قَرَأَ النَّبِيُّ"))


class ChainMatcherTests(SimpleTestCase):
    def test_short_prefix_alone_is_insufficient(self):
        matcher = ChainMatcher({101: Narrator(arabic_name="سفيان بن سعيد")})
        self.assertEqual(matcher.resolve([("سفيان", "حدثنا")]), [(None, False)])

    def test_later_teacher_breaks_a_tie_using_the_students_list(self):
        narrators = {
            101: Narrator(arabic_name="سفيان بن سعيد"),
            102: Narrator(arabic_name="سفيان بن عيينة"),
            103: Narrator(arabic_name="عمرو بن دينار", students_inds="102"),
            BUKHARI_ID: Narrator(teachers_inds="101, 102"),
        }
        chain = [("سفيان", "حدثنا"), ("عمرو بن دينار", "عن")]
        matcher = ChainMatcher(narrators)
        self.assertEqual(matcher.resolve(chain), [(102, True), (103, True)])
        self.assertEqual(matcher.resolve(chain[:1]), [(None, False)])

    def test_recorded_alias_disambiguates_an_earlier_name(self):
        narrators = {
            101: Narrator(arabic_name="زيد بن سعد"),
            102: Narrator(arabic_name="زيد بن سعد بن سالم", teachers_inds="103"),
            103: Narrator(arabic_name="عمرو بن صالح", aliases="عمرو بن صالح | ابن زينب", teachers_inds="105"),
            104: Narrator(arabic_name="حسن بن زينب"),
            105: Narrator(arabic_name="سالم بن مالك"),
            BUKHARI_ID: Narrator(teachers_inds="102"),
        }
        matcher = ChainMatcher(narrators)
        chain = [("زيد بن سعد", "حدثنا"), ("ابن زينب", "عن"), ("سالم بن مالك", "عن")]
        self.assertEqual([sid for sid, _ in matcher.resolve(chain)], [102, 103, 105])

    def test_two_documented_aliases_still_require_disambiguation(self):
        narrators = {
            101: Narrator(arabic_name="زيد بن سعد", aliases=" | أبو يحيى"),
            102: Narrator(arabic_name="عمرو بن صالح", aliases=" | أبو يحيى"),
        }
        self.assertEqual(ChainMatcher(narrators).resolve([("أبي يحيى", "عن")]), [(None, False)])

    def test_explicit_kunya_does_not_index_its_bare_given_name(self):
        matcher = ChainMatcher({
            101: Narrator(arabic_name="إسماعيل بن إبراهيم", aliases="إسماعيل بن إبراهيم | أبو بشر"),
            BUKHARI_ID: Narrator(teachers_inds="101"),
        })
        self.assertEqual(matcher.resolve([("أبي بشر", "حدثنا")]), [(101, True)])
        self.assertEqual(matcher.resolve([("بشر", "حدثنا")]), [(None, False)])

    def test_advance_matches_exhaustive_search_in_both_directions(self):
        matcher = ChainMatcher({
            101: Narrator(birth_year=140, teachers_inds="104"),
            102: Narrator(birth_year=80, teachers_inds="104", grade="1st generation"),
            103: Narrator(birth_year=90),
            104: Narrator(death_year=130, students_inds="101, 102", grade="3rd generation"),
        })
        student_scores = {101: 20, 102: 8, 103: 10, None: 2}
        teacher_scores = {104: 6, None: 1}
        for backward, current, previous, relatives in (
            (False, teacher_scores, student_scores, matcher.students),
            (True, student_scores, teacher_scores, matcher.teachers),
        ):
            with self.subTest(backward=backward):
                expected = {}
                for candidate, score in current.items():
                    expected[candidate] = score + max(
                        prior + relatives.get(candidate, {}).get(neighbor, 0)
                        + matcher.chronology_score(
                            *((candidate, neighbor) if backward else (neighbor, candidate))
                        )
                        for neighbor, prior in previous.items()
                        if candidate != neighbor or candidate is None
                    )
                self.assertEqual(matcher.advance(current, previous, relatives, backward=backward), expected)
        self.assertEqual(matcher.advance(teacher_scores, student_scores, matcher.students)[104], 19)

    def test_repeated_narrator_is_left_unresolved(self):
        narrators = {
            101: Narrator(arabic_name="زيد بن عمرو"),
            102: Narrator(arabic_name="عمرو بن دينار"),
        }
        chain = [("زيد بن عمرو", "حدثنا"), ("عمرو بن دينار", "عن"), ("زيد بن عمرو", "عن")]
        self.assertEqual(ChainMatcher(narrators).resolve(chain), [(101, False), (102, False), (None, False)])

    def test_father_reference_requires_parent_metadata(self):
        narrators = {
            101: Narrator(arabic_name="هشام بن عروة", teachers_inds="102"),
            102: Narrator(arabic_name="عروة بن الزبير"),
        }
        chain = [("هشام بن عروة", "حدثنا"), ("ابيه", "عن")]
        self.assertEqual(ChainMatcher(narrators).resolve(chain), [(101, False), (None, False)])
        narrators[101].parents = "Urwa [102] / Umm Walad"
        self.assertEqual(ChainMatcher(narrators).resolve(chain), [(101, False), (102, True)])

    def test_chain_switch_starts_again_from_bukhari(self):
        narrators = {
            101: Narrator(arabic_name="سفيان بن سعيد"),
            102: Narrator(arabic_name="سفيان بن عيينة"),
            103: Narrator(arabic_name="عمرو بن دينار", teachers_inds="101"),
            BUKHARI_ID: Narrator(teachers_inds="102"),
        }
        text = "حدثنا عمرو بن دينار عن سفيان ، ح ، حدثنا سفيان"
        matcher = ChainMatcher(narrators)
        self.assertEqual(
            [matcher.resolve(chain) for chain in extract_chains(text)],
            [[(103, False), (101, True)], [(102, True)]],
        )


class SuspendedChainTests(SimpleTestCase):
    def test_quotation_does_not_create_a_compiler_to_prophet_link(self):
        text = "قالت زينب فدخلت على زينب ثم قالت سمعت رسول الله"
        self.assertEqual(extract_chains(text), [])

    def test_named_suspended_chain_does_not_use_al_bukharis_teacher_list(self):
        narrators = {
            101: Narrator(arabic_name="سفيان بن سعيد"),
            102: Narrator(arabic_name="سفيان بن عيينة"),
            103: Narrator(arabic_name="عمرو بن دينار"),
            BUKHARI_ID: Narrator(teachers_inds="102"),
        }
        chain, = extract_chains("وقال سفيان حدثني عمرو بن دينار")
        self.assertEqual(chain[0], ("سفيان", "قال"))
        self.assertEqual(ChainMatcher(narrators).resolve(chain), [(None, False), (103, False)])


class ChronologyTests(SimpleTestCase):
    def test_teacher_who_died_before_students_birth_is_not_selected(self):
        narrators = {
            101: Narrator(arabic_name="زيد بن عمر", birth_year=100, teachers_inds="102, 103"),
            102: Narrator(arabic_name="سفيان بن سعيد", death_year=89, students_inds="101"),
            103: Narrator(arabic_name="سفيان بن عيينة", death_year=150),
        }
        chain = [("زيد بن عمر", "حدثنا"), ("سفيان", "عن")]
        self.assertEqual(ChainMatcher(narrators).resolve(chain), [(101, False), (103, True)])


class CorrectedDatabaseApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        selected = {"1", "5", "15", "19", "94", "402", "402b", "765", "1067", "7478"}
        with TemporaryDirectory() as directory:
            source = DATA_DIR / "Sahih al-Bukhari.csv"
            subset = Path(directory) / "hadiths.csv"
            with source.open(encoding="utf-8-sig", newline="") as input_file:
                reader = csv.DictReader(input_file)
                with subset.open("w", encoding="utf-8", newline="") as output_file:
                    writer = csv.DictWriter(output_file, fieldnames=reader.fieldnames)
                    writer.writeheader()
                    writer.writerows(row for row in reader if row["Reference"].rsplit(":", 1)[-1] in selected)
            call_command("load_bukhari", bukhari=str(subset), stdout=StringIO())

    def test_hadith_search_prioritizes_exact_number_and_searches_both_languages(self):
        response = self.client.get("/api/v1/hadiths/", {"search": "5", "compact": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["hadith_number"], "5")
        self.assertNotIn("arabic_matn", response.data["results"][0])

        for term in ("رَسُولُ اللَّهِ", "revelation"):
            with self.subTest(term=term):
                response = self.client.get("/api/v1/hadiths/", {"search": term, "compact": 1})
                self.assertIn("5", {row["hadith_number"] for row in response.data["results"]})

    def test_hadith_5_ends_with_ibn_abbas(self):
        result = self.client.get("/api/v1/hadiths/5/?chain=1")
        self.assertEqual(result.status_code, 200)
        self.assertEqual([edge["teacher"] for edge in result.data["edges"]], [20040, 20469, 11399, 11050, 17])
        self.assertIn("رَسُولُ اللَّهِ", result.data["arabic_matn"])
        self.assertNotIn(1, {narrator["id"] for narrator in result.data["narrators"]})

    def test_explicit_prophet_transmissions_end_with_prophet(self):
        for number, student, term in ((1, 3, "سمعت"), (19, None, "قال"), (94, 19, "عن"), (765, 871, "سمعت")):
            with self.subTest(number=number):
                result = self.client.get(f"/api/v1/hadiths/{number}/?chain=1")
                self.assertEqual(result.status_code, 200)
                last = result.data["edges"][-1]
                self.assertEqual(last["teacher"], 1)
                self.assertEqual(last["terminology"], term)
                if student is not None:
                    self.assertEqual(last["student"], student)

    def test_nested_question_does_not_supply_a_direct_transmission(self):
        result = self.client.get("/api/v1/hadiths/7478/?chain=1")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["edges"][-1]["teacher"], 17)
        self.assertNotIn(1, {edge["teacher"] for edge in result.data["edges"]})

    def test_hadith_1067_and_related_endpoints(self):
        response = self.client.get("/api/v1/hadiths/1067/?chain=1")
        self.assertEqual(response.status_code, 200)
        ids = [30001, 30160, 20278, 20020, 11049, 11054, 16]
        pairs = list(zip(ids[:-1], ids[1:]))
        self.assertEqual([(edge["student"], edge["teacher"]) for edge in response.data["edges"]], pairs)
        self.assertEqual({narrator["id"] for narrator in response.data["narrators"]}, set(ids))
        for resource, count in (("edges", 6), ("narrators", 7)):
            result = self.client.get(f"/api/v1/{resource}/?hadith_number=1067")
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.data["count"], count)

    def test_parallel_chains_are_separate_and_contiguous(self):
        result = self.client.get("/api/v1/hadiths/15/?chain=1")
        self.assertEqual(result.status_code, 200)
        for index, length in ((0, 5), (1, 5)):
            edges = [edge for edge in result.data["edges"] if edge["chain_index"] == index]
            self.assertEqual(len(edges), length)
            self.assertEqual(edges[0]["student"], BUKHARI_ID)
            self.assertEqual(edges[-1]["teacher"], 1)
            self.assertEqual([edge["teacher"] for edge in edges[:-1]],
                             [edge["student"] for edge in edges[1:]])
            expected_route = (
                [30400, 20208, 11295, 19, 1] if index == 0 else [20404, 20020, 11019, 19, 1]
            )
            self.assertEqual([edge["teacher"] for edge in edges], expected_route)

    def test_variant_reference_has_its_own_record_and_edges(self):
        base = self.client.get("/api/v1/hadiths/402/?chain=1")
        variant = self.client.get("/api/v1/hadiths/402b/?chain=1")
        self.assertEqual(variant.status_code, 200)
        self.assertEqual(variant.data["hadith_number"], "402b")
        self.assertNotEqual(base.data["id"], variant.data["id"])
        self.assertTrue(variant.data["edges"])
        self.assertEqual(self.client.get("/api/v1/hadiths/402z/").status_code, 404)

    def test_import_refuses_to_change_populated_tables(self):
        counts = (Narrator.objects.count(), Hadith.objects.count(), TransmissionEdge.objects.count())
        with self.assertRaisesMessage(CommandError, "isnad tables must be empty"):
            call_command("load_bukhari", stdout=StringIO())
        self.assertEqual((Narrator.objects.count(), Hadith.objects.count(), TransmissionEdge.objects.count()), counts)


class NarratorProfileApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        Narrator.objects.bulk_create([
            Narrator(
                id=1, name="Narrator one", arabic_name="الراوي الأول",
                aliases="أبو زيد", biography="هذه ترجمة عربية محفوظة.\nوفيها سطر ثانٍ.",
                teachers_inds="9, 2, 9, 404, NA, -1, 2147483648",
                students_inds="2, 9", tags="Recitation/Quran", parents="زيد",
            ),
            Narrator(id=2, name="Narrator two", arabic_name="الراوي الثاني", biography="Recitation/Quran"),
            Narrator(id=9, name="Narrator nine", arabic_name="الراوي التاسع"),
            Narrator(id=10, name="Narrator ten", arabic_name="الراوي العاشر"),
            Narrator(id=800000, name="Unresolved narrator"),
        ])
        hadith = Hadith.objects.create(hadith_number="1")
        TransmissionEdge.objects.bulk_create([
            TransmissionEdge(hadith=hadith, teacher_id=1, student_id=student, sequence=index)
            for index, student in enumerate((2, 10, 10, 800000))
        ])

    def test_detail_batches_related_names_preserves_order_and_reports_missing_ids(self):
        with self.assertNumQueries(3):
            response = self.client.get("/api/v1/narrators/1/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["teachers_inds"], "9, 2, 9, 404, NA, -1, 2147483648")
        self.assertEqual(response.data["teachers"], [
            {"id": 9, "name": "Narrator nine", "arabic_name": "الراوي التاسع"},
            {"id": 2, "name": "Narrator two", "arabic_name": "الراوي الثاني"},
            {"id": 404, "name": None, "arabic_name": None},
        ])
        self.assertEqual([record["id"] for record in response.data["students"]], [2, 9])
        self.assertEqual(response.data["students_inds"], "2, 9")
        self.assertEqual([record["id"] for record in response.data["transmission_students"]], [2, 10])
        self.assertIn("الراوي الأول".encode("utf-8"), response.content)
        self.assertEqual(response.json()["biography"], "هذه ترجمة عربية محفوظة.\nوفيها سطر ثانٍ.")
        self.assertEqual(response.data["aliases"], "أبو زيد")
        self.assertEqual(response.data["parents"], "زيد")

    def test_related_detail_and_compact_search_are_independent(self):
        with self.assertNumQueries(2):
            related = self.client.get("/api/v1/narrators/2/")
        self.assertEqual(related.status_code, 200)
        self.assertEqual(related.data["biography"], "Recitation/Quran")
        self.assertEqual(related.data["teachers"], [])
        self.assertEqual(related.data["students"], [])
        self.assertEqual(self.client.get("/api/v1/narrators/404/").status_code, 404)
        search = self.client.get("/api/v1/narrators/", {"search": "الراوي الثاني"})
        self.assertEqual(search.status_code, 200)
        self.assertEqual([row["id"] for row in search.data["results"]], [2])
        self.assertNotIn("teachers", search.data["results"][0])


class KnowledgeGraphTests(SimpleTestCase):
    def test_hadith_endpoint_keeps_sanads_separate_and_orders_edges(self):
        import json

        sanads = [
            {"sanadId": 12, "grade": "صحيح", "chain": [{"rawiId": 11}, {"rawiId": 21}, {"rawiId": 31}]},
            {"sanadId": 13, "chain": [{"rawiId": 11}, {"rawiId": 41}]},
        ]
        with patch("isnad.knowledge_graph.urlopen", return_value=StringIO(json.dumps({"sanads": sanads}))) as upstream:
            response = self.client.get("/api/v1/knowledge-graph/hadiths/17154/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(upstream.call_args.args[0].endswith("/api/hadith/17154"))
        chains = response.json()["visual_isnad_chains"]
        self.assertEqual([chain["sanad_id"] for chain in chains], [12, 13])
        self.assertEqual(chains[0]["grade"], "صحيح")
        self.assertEqual(
            [[(edge["teacher"], edge["student"]) for edge in chain["edges"]] for chain in chains],
            [[(1000021, 1000011), (1000031, 1000021)], [(1000041, 1000011)]],
        )

    def test_rawi_endpoint_preserves_teachers_students_and_evaluations(self):
        payload = '{"teachers":[{"id":2}],"students":[{"id":3}],"aqwal":[{"alemId":4}]}'
        with patch("isnad.knowledge_graph.urlopen", return_value=StringIO(payload)) as upstream:
            response = self.client.get("/api/v1/knowledge-graph/rawis/1/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(upstream.call_args.args[0].endswith("/api/rawi/1"))
        self.assertEqual(response.json(), {
            "teachers": [{"id": 2}],
            "students": [{"id": 3}],
            "aqwal": [{"alemId": 4}],
        })

    def test_malformed_hadith_from_upstream_returns_bad_gateway(self):
        payload = '{"sanads":[{"sanadId":12,"chain":[{}]}]}'
        with patch("isnad.knowledge_graph.urlopen", return_value=StringIO(payload)):
            response = self.client.get("/api/v1/knowledge-graph/hadiths/17154/")

        self.assertEqual(response.status_code, 502)

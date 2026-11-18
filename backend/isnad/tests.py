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
        selected = {"1", "15", "402", "402b", "1067"}
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
            if index == 1:
                self.assertEqual([edge["teacher"] for edge in edges], [20404, 20020, 11019, 19, 1])

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

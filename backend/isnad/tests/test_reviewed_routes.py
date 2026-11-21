from copy import deepcopy

from django.test import SimpleTestCase

from isnad.models import Hadith
from isnad.reviewed_routes import correct_legacy_bukhari_15, supplemental_profile


class ReviewedRouteTests(SimpleTestCase):
    def setUp(self):
        self.hadith = Hadith(
            id=15, reference_url="https://sunnah.com/bukhari:15",
            arabic_isnad=(
                "حدثنا يعقوب بن إبراهيم قال حدثنا ابن علية عن عبد العزيز بن صهيب "
                "عن أنس عن النبي صلى الله عليه وسلم ح وحدثنا آدم قال حدثنا شعبة "
                "عن قتادة عن أنس قال قال النبي صلى الله عليه وسلم"
            ),
        )
        paths = ((30001, 20184, 5888, 11295, 19, 1), (30001, 20404, 20020, 11019, 19))
        self.raw = [
            {"id": 91 + index, "student": student, "teacher": teacher,
             "sequence": index, "chain_index": None}
            for index, (student, teacher) in enumerate(
                (student, teacher) for path in paths for student, teacher in zip(path, path[1:])
            )
        ]

    def test_corrects_first_route_and_preserves_second_route_and_raw_edges(self):
        original = deepcopy(self.raw)
        display = correct_legacy_bukhari_15(self.hadith, self.raw)
        self.assertEqual(self.raw, original)
        self.assertEqual(display[5:], original[5:])
        first = display[:5]
        self.assertEqual([first[0]["student"]] + [e["teacher"] for e in first],
                         [30001, 30400, 20208, 11295, 19, 1])
        self.assertTrue(all(a["teacher"] == b["student"] for a, b in zip(first, first[1:])))
        self.assertEqual([e["id"] for e in display], list(range(91, 100)))
        self.assertTrue(all(e["chain_index"] is None for e in display))
        self.assertEqual(display[1]["correction"]["original_teacher"], 5888)

    def test_declines_different_source_and_different_route_metadata(self):
        for field, value in (("reference_url", "https://sunnah.com/bukhari:1381"),
                             ("arabic_isnad", "حدثنا يعقوب")):
            with self.subTest(field=field):
                different = deepcopy(self.hadith)
                setattr(different, field, value)
                self.assertIs(correct_legacy_bukhari_15(different, self.raw), self.raw)
        self.raw[0]["chain_index"] = 0
        self.assertIs(correct_legacy_bukhari_15(self.hadith, self.raw), self.raw)

    def test_supplement_uses_documented_canonical_id(self):
        person = supplemental_profile(20208)
        self.assertEqual(person.pk, 20208)
        self.assertEqual(person.arabic_name, "إسماعيل بن إبراهيم بن مقسم")
        self.assertIn("ابن علية", person.aliases)
        self.assertIsNone(supplemental_profile(5888))


class AdditionalReviewedRouteTests(SimpleTestCase):
    def test_all_twelve_corrections_keep_existing_edge_ids_and_order(self):
        from isnad.reviewed_routes import correct_reviewed_legacy_route, reviewed_narrator_routes

        routes = reviewed_narrator_routes()
        expected = {
            1191: [30001,30400,20208,11015,11014],
            1381: [30001,30400,20208,11295,19,1],
            1573: [30001,30400,20208,11015,800888],
            1639: [30001,30400,20208,11015,11014,800921,1],
            2768: [30001,30400,20208,11295,801573,1],
            3063: [30001,30400,20208,11015,11281,19,1],
            3195: [30001,10950,20208,20449,11449,11213,1],
            4020: [30001,30400,20208,11289,19,1],
            4617: [30001,30400,20208],
            5225: [30001,30026,20208,11279,19],
            5549: [30001,30343,20208,11015,11035,19],
            6132: [30001,30143,20208,11015,11090],
        }
        self.assertEqual(len(routes), len(expected))
        for number, expected_path in expected.items():
            url = f"https://sunnah.com/bukhari:{number}"
            review = routes[url]
            with self.subTest(hadith=number):
                hadith = Hadith(reference_url=url, arabic_isnad=review["isnad"])
                raw = [
                    {"id": i + 115, "sequence": i, "student": student, "teacher": teacher,
                     "chain_index": None}
                    for i, student, teacher in review["edges"]
                ]
                original = deepcopy(raw)
                result = correct_reviewed_legacy_route(hadith, raw)
                self.assertEqual(raw, original)
                self.assertEqual([e["id"] for e in result], [e["id"] for e in raw])
                self.assertEqual([(e["student"], e["teacher"]) for e in result],
                                 list(zip(expected_path, expected_path[1:])))
                self.assertTrue(all(e["chain_index"] is None for e in result))
                for old, new in zip(raw, result):
                    if new != old:
                        self.assertEqual(new["correction"]["original_teacher"], old["teacher"])
                        self.assertEqual(new["correction"]["original_student"], old["student"])
                raw[0]["chain_index"] = 0
                self.assertIs(correct_reviewed_legacy_route(hadith, raw), raw)
                raw[0]["chain_index"] = None
                raw[0]["teacher"] = 99999
                self.assertIs(correct_reviewed_legacy_route(hadith, raw), raw)
                other = Hadith(reference_url=url + "0", arabic_isnad=review["isnad"])
                self.assertIs(correct_reviewed_legacy_route(other, original), original)
                hadith.arabic_isnad += " لفظ مختلف"
                self.assertIs(correct_reviewed_legacy_route(hadith, original), original)

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

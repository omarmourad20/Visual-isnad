from django.test import SimpleTestCase

from isnad.management.commands.load_bukhari import ChainMatcher, name_key
from isnad.models import Narrator


class NarratorHonorificTests(SimpleTestCase):
    def test_recognizes_full_and_truncated_honorifics_without_removing_names(self):
        for suffix in ("صلى الله عليه", "صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ", "رضي الله عنها", "رحمه الله"):
            with self.subTest(suffix=suffix):
                self.assertEqual(name_key(f"نوبة خادم النبي {suffix}"), "نوبه خادم النبي")
        self.assertEqual(name_key("ابن عُلَيَّةَ"), "بن عليه")

    def test_false_candidate_not_indexed_and_documented_alias_retained(self):
        nauba = Narrator(id=5888, arabic_name="نوبة خادم النبي صلى الله عليه",
                         aliases="نوبة خادم النبي صلى الله عليه")
        ismail = Narrator(id=20208, arabic_name="إسماعيل بن إبراهيم بن مقسم", aliases="إسماعيل | ابن علية")
        matcher = ChainMatcher({n.pk: n for n in [nauba, ismail]})
        self.assertNotIn(5888, matcher.candidates(name_key("عليه"), {}))
        self.assertNotIn(5888, matcher.candidates(name_key("ابن علية"), {}))
        self.assertIn(20208, matcher.candidates(name_key("ابن علية"), {}))
        self.assertIn(5888, matcher.candidates(name_key("نوبة خادم النبي"), {}))

    def test_real_name_with_the_same_spelling_is_preserved(self):
        real = Narrator(id=31, arabic_name="عليه بن زياد")
        other = Narrator(id=32, arabic_name="خالد عليه بن يزيد")
        matcher = ChainMatcher({31: real, 32: other})
        self.assertIn(31, matcher.candidates(name_key("عليه بن زياد"), {}))
        self.assertNotIn(32, matcher.candidates(name_key("عليه"), {}))

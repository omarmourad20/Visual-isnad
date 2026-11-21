from django.test import SimpleTestCase

from isnad.management.commands.load_bukhari import (
    _names_from_segment, extract_chains, normalize_arabic, split_isnad_matn,
)
from isnad.reviewed_routes import route_evidence


class NarrativeBoundaryTests(SimpleTestCase):
    def test_bukhari_7000_extracts_only_named_opening_transmitters(self):
        source = route_evidence()["https://sunnah.com/bukhari:7000"]["isnad"]
        opening, body = split_isnad_matn(source)
        self.assertIn("أَنَّ رَجُلاً", body)
        self.assertEqual(source, opening + " " + body)
        self.assertEqual(
            [[name for name, _ in chain] for chain in extract_chains(opening)],
            [["يحيي", "الليث", "يونس", "ابن شهاب", "عبيد الله بن عبد الله", "ابن عباس"]],
        )

    def test_confirmed_fragments_cannot_use_short_name_fallback(self):
        for fragment in (
            "النبي وقال الزبيدي", "ابن عباس أو أبا هريرة",
            "النبي وقال شعيب وإسحاق بن يحيى", "الزهري كان أبو هريرة يحدث",
            "النبي وكان معمر لا يسنده حتى كان بعد",
        ):
            with self.subTest(fragment=fragment):
                self.assertEqual(_names_from_segment(normalize_arabic(fragment), "قال"), [])

    def test_explicit_prophet_attribution_before_a_route_switch_survives(self):
        self.assertEqual(
            _names_from_segment("النبي وقال الزبيدي", "عن"),
            [("رسول الله", "عن")],
        )

    def test_bukhari_7046_keeps_ibn_abbas_before_the_dream_report(self):
        source = (
            "حَدَّثَنِي يَحْيَى بْنُ بُكَيْرٍ، حَدَّثَنَا اللَّيْثُ، عَنْ يُونُسَ، عَنِ ابْنِ شِهَابٍ، "
            "عَنْ عُبَيْدِ اللَّهِ بْنِ عَبْدِ اللَّهِ بْنِ عُتْبَةَ، أَنَّ ابْنَ عَبَّاسٍ ـ رضى الله عنهما ـ "
            "كَانَ يُحَدِّثُ أَنَّ رَجُلاً أَتَى رَسُولَ اللَّهِ صلى الله عليه وسلم فَقَالَ إِنِّي رَأَيْتُ "
            "اللَّيْلَةَ فِي الْمَنَامِ ظُلَّةً تَنْطِفُ السَّمْنَ وَالْعَسَلَ"
        )
        opening, body = split_isnad_matn(source)
        self.assertTrue(body.startswith("أَنَّ رَجُلاً"))
        chain, = extract_chains(opening)
        self.assertEqual(chain[-1], ("ابن عباس", "ان"))

from types import SimpleNamespace

from django.test import SimpleTestCase

from isnad.reviewed_routes import (
    apply_path_identity_review, correct_reviewed_legacy_route, describe_reviewed_routes,
    route_evidence, withheld_route_reason,
)


class IsnadRouteEvidenceTests(SimpleTestCase):
    def record(self, number):
        url = f"https://sunnah.com/bukhari:{number}"
        evidence = route_evidence()[url]
        hadith = SimpleNamespace(reference_url=url, arabic_isnad=evidence["isnad"])
        edges = [
            {"id": 45000 + sequence, "sequence": sequence, "student": student, "teacher": teacher, "chain_index": None}
            for sequence, student, teacher in evidence["legacy_edges"]
        ]
        return hadith, edges

    def test_legacy_bukhari_15_has_source_boundaries_and_missing_second_terminal(self):
        hadith, raw = self.record(15)
        edges = correct_reviewed_legacy_route(hadith, raw)
        first, second = describe_reviewed_routes(hadith, raw, edges)
        self.assertEqual(first["status"], "reviewed")
        self.assertEqual(first["edge_ids"], list(range(45000, 45005)))
        self.assertEqual(second["status"], "legacy_segment")
        self.assertEqual(second["edge_ids"], list(range(45005, 45009)))
        self.assertEqual([edge["teacher"] for edge in edges if edge["id"] in second["edge_ids"]],
                         [20404, 20020, 11019, 19])

    def test_indexed_hadith_15_has_two_source_reviewed_routes(self):
        hadith, _ = self.record(15)
        paths = route_evidence()[hadith.reference_url]["indexed_paths"]
        edges = [
            {"id": 100 * index + sequence, "sequence": sequence, "student": student,
             "teacher": teacher, "chain_index": index}
            for index, path in enumerate(paths)
            for sequence, (student, teacher) in enumerate(zip(path, path[1:]), 1)
        ]
        self.assertEqual([route["status"] for route in describe_reviewed_routes(hadith, edges, edges)],
                         ["reviewed", "reviewed"])
        edges[-1]["teacher"] = 58
        self.assertEqual(describe_reviewed_routes(hadith, edges, edges), [])

    def test_identity_corrections_require_matching_source_and_stored_edges(self):
        for number, expected in [(5, 17), (1067, 16)]:
            with self.subTest(number=number):
                hadith, raw = self.record(number)
                edges = apply_path_identity_review(hadith, raw)
                self.assertEqual([edge["id"] for edge in edges], [edge["id"] for edge in raw])
                self.assertEqual(edges[-1]["teacher"], expected)
                self.assertEqual(edges[-1]["correction"]["original_teacher"], raw[-1]["teacher"])
                self.assertTrue(all(edge["teacher"] != 1 for edge in edges))
                self.assertEqual(describe_reviewed_routes(hadith, raw, edges)[0]["status"], "reviewed")
                hadith.arabic_isnad += " كلام آخر"
                self.assertIs(apply_path_identity_review(hadith, raw), raw)

    def test_withheld_import_retains_raw_edge_records_and_requires_matching_signature(self):
        for number in [32, 74, 188, 1185]:
            with self.subTest(number=number):
                hadith, raw = self.record(number)
                self.assertTrue(withheld_route_reason(hadith, raw))
                self.assertEqual(describe_reviewed_routes(hadith, raw, raw), [])
                raw[0]["teacher"] = 40003
                self.assertIsNone(withheld_route_reason(hadith, raw))

    def test_review_preserves_prophet_where_supported_and_does_not_append_him_to_5225(self):
        for number, terminal in [(1, 1), (832, 1), (1381, 1), (5225, 19)]:
            with self.subTest(number=number):
                hadith, raw = self.record(number)
                edges = correct_reviewed_legacy_route(hadith, raw)
                self.assertEqual(len(raw), len(edges))
                self.assertEqual(edges[-1]["teacher"], terminal)
                route, = describe_reviewed_routes(hadith, raw, edges)
                self.assertEqual(route["edge_ids"], [edge["id"] for edge in raw])

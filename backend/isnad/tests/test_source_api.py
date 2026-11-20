import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import URLError

from django.test import override_settings
from rest_framework.test import APITestCase

from isnad.models import Hadith
from isnad.review_source_proposals import BINDINGS, review
from isnad.source_api import local_record
from isnad.source_crosswalk import build_crosswalk
from isnad.source_matching import HadithRecord


class SourceAPITests(APITestCase):
    def setUp(self):
        self.hadith = Hadith.objects.create(
            id=15, hadith_number="15", book_title="Sahih al-Bukhari", arabic_matn="إنما الأعمال بالنيات",
        )
        self.candidate = HadithRecord("hadith_kg", "pinned", "14", "صحيح البخاري", "انما الاعمال بالنيات")
        self.bundle = build_crosswalk([local_record(self.hadith)], [self.candidate])
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        manifest = Path(directory.name) / "sources.json"
        manifest.write_text(json.dumps(self.bundle), encoding="utf-8")
        settings = override_settings(HADITH_SOURCE_CROSSWALK=str(manifest))
        settings.enable()
        self.addCleanup(settings.disable)
        self.root = "/api/v1/hadiths/15/"
        self.routes = self.root + "source-routes/"
        self.params = {"source_key": "hadith_kg:pinned:14"}

    def test_proposal_uses_external_id_and_remains_unreviewed(self):
        response = self.client.get(self.root + "sources/", {"page_size": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        row = response.json()["results"][0]
        self.assertEqual(row["right_key"], "hadith_kg:pinned:14")
        self.assertEqual(row["status"], "review_required")
        self.assertEqual(row["evidence"], "matn")

    def test_live_routes_remain_separate_and_do_not_write(self):
        fixture = {"bookId": 1, "matnClean": self.candidate.arabic_matn, "sanads": [
            {"sanadId": 29, "chain": [{"rawiId": 2}, {"rawiId": 3, "name": "زيد"}]},
            {"sanadId": 30, "chain": [{"rawiId": 2}, {"rawiId": 4, "name": "عمرو"}]},
        ]}
        original = self.client.get(self.root + "?chain=1").json()
        with patch("isnad.knowledge_graph.urlopen", return_value=BytesIO(json.dumps(fixture).encode())) as upstream:
            result = self.client.get(self.routes, self.params)
        self.assertEqual(result.status_code, 200)
        self.assertTrue(upstream.call_args.args[0].endswith("/api/hadith/14"))
        routes = result.json()["routes"]
        self.assertEqual([r["sanad_id"] for r in routes], [29, 30])
        self.assertEqual(routes[0]["narrators"][0]["name"], "راوٍ غير معروف")
        self.assertEqual(routes[0]["edges"][0]["terminology"], "")
        self.assertEqual(routes[0]["source"]["status"], "external_unreviewed")
        self.assertEqual(self.client.get(self.root + "?chain=1").json(), original)

    def test_unlisted_route_and_stale_text_are_not_previewed(self):
        with patch("isnad.knowledge_graph.urlopen") as upstream:
            self.assertEqual(self.client.get(self.routes, {"source_key": "other"}).status_code, 404)
            self.hadith.arabic_matn = "نص مختلف"
            self.hadith.save(update_fields=["arabic_matn"])
            self.assertEqual(self.client.get(self.routes, self.params).status_code, 404)
        upstream.assert_not_called()

    def test_service_error_and_drift_fail_closed(self):
        with patch("isnad.knowledge_graph.urlopen", side_effect=URLError("offline")):
            self.assertEqual(self.client.get(self.routes, self.params).status_code, 502)
        with patch("isnad.knowledge_graph.urlopen", return_value=BytesIO(b'{"bookId":1,"nass":"other"}')):
            self.assertEqual(self.client.get(self.routes, self.params).status_code, 409)

    def test_review_requires_current_evidence_and_does_not_adopt_a_route(self):
        proposal = self.bundle["proposals"][0]
        decision = {key: proposal[key] for key in BINDINGS}
        decision.update(decision="accepted_text_reference", reviewer="Reviewer", evidence="Checked edition text")
        manifest = review(self.bundle, [decision])
        self.assertEqual(manifest["unreviewed_count"], 0)
        self.assertEqual(manifest["policy"], "text_reference_review_only_no_chain_adoption")
        with self.assertRaises(ValueError):
            review(self.bundle, [{**decision, "right_text_digest": "stale"}])

    def test_many_to_one_is_ambiguous(self):
        other = HadithRecord("visual_isnad", "", "16", "صحيح البخاري", self.candidate.arabic_matn)
        result = build_crosswalk([local_record(self.hadith), other], [self.candidate])
        self.assertEqual(result["counts"]["ambiguous_left"], 2)
        self.assertTrue(all(row["confidence"] == "ambiguous" for row in result["proposals"]))

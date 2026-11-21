import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

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
        self.settings_path = manifest
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

    def test_text_proposal_never_opens_unreviewed_routes(self):
        original = self.client.get(self.root + "?chain=1").json()
        with patch("isnad.knowledge_graph.urlopen") as upstream:
            result = self.client.get(self.routes, self.params)
        self.assertEqual(result.status_code, 404)
        upstream.assert_not_called()
        self.assertFalse(self.client.get(self.root + "sources/").json()["results"][0]["can_preview_routes"])
        self.assertEqual(self.client.get(self.root + "?chain=1").json(), original)

    def test_review_requires_current_evidence_and_does_not_adopt_a_route(self):
        proposal = self.bundle["proposals"][0]
        decision = {key: proposal[key] for key in BINDINGS}
        decision.update(decision="accepted_text_reference", reviewer="Reviewer", evidence="Checked edition text")
        manifest = review(self.bundle, [decision])
        self.assertEqual(manifest["unreviewed_count"], 0)
        self.assertEqual(manifest["policy"], "text_reference_review_only_no_chain_adoption")
        with self.assertRaises(ValueError):
            review(self.bundle, [{**decision, "right_text_digest": "stale"}])

    def test_no_match_is_distinct_from_missing_configuration_and_stale_data(self):
        Hadith.objects.create(id=16, hadith_number="16", book_title="Sahih al-Bukhari", arabic_matn="غيره")
        empty = self.client.get("/api/v1/hadiths/16/sources/").json()
        self.assertEqual((empty["status"], empty["count"]), ("available", 0))
        self.hadith.arabic_matn = "نص مختلف"
        self.hadith.save(update_fields=["arabic_matn"])
        self.assertEqual(self.client.get(self.root + "sources/").json()["status"], "stale")
        with self.settings(HADITH_SOURCE_CROSSWALK=""):
            self.assertEqual(self.client.get(self.root + "sources/").json()["status"], "not_configured")

    def test_many_to_one_is_ambiguous(self):
        other = HadithRecord("visual_isnad", "", "16", "صحيح البخاري", self.candidate.arabic_matn)
        result = build_crosswalk([local_record(self.hadith), other], [self.candidate])
        self.assertEqual(result["counts"]["ambiguous_left"], 2)
        self.assertTrue(all(row["confidence"] == "ambiguous" for row in result["proposals"]))

    def test_crosswalk_rows_without_explicit_bukhari_metadata_are_hidden(self):
        row = self.bundle["proposals"][0]
        for collection in (None, "سنن أبي داود"):
            row["right_collection"] = collection
            self.settings_path.write_text(json.dumps(self.bundle), encoding="utf-8")
            self.assertEqual(self.client.get(self.root + "sources/").json()["results"], [])
            self.assertEqual(self.client.get(self.routes, self.params).status_code, 404)

    def test_ambiguous_proposal_stays_visible_without_route_preview(self):
        duplicate = HadithRecord("hadith_kg", "pinned", "44", "صحيح البخاري", self.candidate.arabic_matn)
        bundle = build_crosswalk([local_record(self.hadith)], [self.candidate, duplicate])
        self.settings_path.write_text(json.dumps(bundle), encoding="utf-8")
        rows = self.client.get(self.root + "sources/").json()["results"]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["confidence"] == "ambiguous" and not row["can_preview_routes"] for row in rows))
        with patch("isnad.knowledge_graph.urlopen") as upstream:
            self.assertEqual(self.client.get(self.routes, self.params).status_code, 404)
        upstream.assert_not_called()

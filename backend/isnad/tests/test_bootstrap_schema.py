from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from isnad.models import Hadith, Narrator, TransmissionEdge


class BootstrapSchemaTests(SimpleTestCase):
    """Exercise bootstrap and its real serializers without a database or migrations."""

    def check_bootstrap(self, indexed):
        hadith = Hadith(id=1, hadith_number="1", book_title="Sahih al-Bukhari")
        narrators = [Narrator(id=2, name="Student"), Narrator(id=1, name="Teacher")]
        fields = {"id": 17, "hadith_id": 1, "student_id": 2, "teacher_id": 1,
                  "terminology": "عن", "sequence": 4}
        if indexed:
            edge = TransmissionEdge(**fields, chain_index=3)
        else:
            # Model a Django row returned without the column. Accessing its
            # deferred value would require a database, forbidden by SimpleTestCase.
            edge = TransmissionEdge.from_db("default", list(fields), list(fields.values()))
            self.assertEqual(edge.get_deferred_fields(), {"chain_index"})
        rows = MagicMock()
        rows.db = "default"
        rows.__iter__.return_value = iter([edge])
        rows.defer.return_value = rows
        with (
            patch("isnad.views.book_catalog", return_value=[]),
            patch("isnad.views.Hadith.objects.filter") as hadiths,
            patch("isnad.views.TransmissionEdge.objects.filter") as edges,
            patch("isnad.views.Narrator.objects.filter") as people,
            patch("isnad.views.has_chain_index", return_value=indexed),
        ):
            hadiths.return_value.first.return_value = hadith
            edges.return_value.order_by.return_value = rows
            people.return_value.only.return_value = narrators
            response = self.client.get("/api/v1/hadiths/bootstrap/")
        self.assertEqual(response.status_code, 200)
        edges.return_value.order_by.assert_called_once_with("sequence", "id")
        if indexed:
            rows.defer.assert_not_called()
        else:
            rows.defer.assert_called_once_with("chain_index")
        payload = response.json()
        self.assertEqual(payload["hadith"]["hadith_number"], "1")
        self.assertIs(payload["chain_index_available"], indexed)
        self.assertIs(payload["chain_boundaries_recorded"], indexed)
        self.assertEqual({row["id"] for row in payload["narrators"]}, {1, 2})
        self.assertEqual(payload["edges"], [{
            "id": 17, "hadith": 1, "student": 2, "teacher": 1, "sequence": 4,
            "terminology": "عن", "chain_index": 3 if indexed else None,
        }])
        self.assertEqual(payload["hadith"]["edges"], payload["edges"])

    def test_legacy_bootstrap_keeps_edges_without_reading_missing_column(self):
        self.check_bootstrap(indexed=False)

    def test_indexed_bootstrap_preserves_stored_route_index(self):
        self.check_bootstrap(indexed=True)

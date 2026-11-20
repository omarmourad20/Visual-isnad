from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from isnad.edge_schema import has_chain_index
from isnad.models import Hadith, Narrator, TransmissionEdge


class LegacyEdgeSchemaTests(TransactionTestCase):
    def test_legacy_http_reads_preserve_edges_and_forward_migration_keeps_unknown_index(self):
        previous = [("isnad", "0002_hadith_indexes_and_book_number")]
        current = [("isnad", "0003_transmissionedge_chain_index")]
        hadith = Hadith.objects.create(id=15, hadith_number="15", book_title="Sahih al-Bukhari")
        student = Narrator.objects.create(id=2, name="Student")
        teacher = Narrator.objects.create(id=3, name="Teacher")
        edge = TransmissionEdge.objects.create(
            hadith=hadith, student=student, teacher=teacher, terminology="عن", sequence=7,
        )
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(current))
        MigrationExecutor(connection).migrate(previous)
        self.assertFalse(has_chain_index())
        client = APIClient()
        detail = client.get("/api/v1/hadiths/15/?chain=1")
        self.assertEqual(detail.status_code, 200)
        self.assertFalse(detail.json()["chain_index_available"])
        expected = detail.json()["edges"][0]
        self.assertEqual((expected["id"], expected["student"], expected["teacher"], expected["sequence"]),
                         (edge.pk, 2, 3, 7))
        self.assertIsNone(expected["chain_index"])
        self.assertEqual(client.get(f"/api/v1/edges/{edge.pk}/").json(), expected)
        edge_list = client.get("/api/v1/edges/", {"hadith_number": "15"}).json()
        self.assertEqual(edge_list["results"], [expected])
        self.assertEqual(client.get("/api/v1/narrators/3/").status_code, 200)
        bootstrap = client.get("/api/v1/hadiths/bootstrap/").json()
        self.assertEqual(bootstrap["hadith"]["edges"], [expected])
        self.assertFalse(bootstrap["chain_index_available"])
        user = get_user_model().objects.create_user(username="editor", is_staff=True)
        client.force_authenticate(user=user)
        self.assertEqual(client.patch(f"/api/v1/edges/{edge.pk}/", {"sequence": 8}).status_code, 409)

        MigrationExecutor(connection).migrate(current)
        self.assertTrue(has_chain_index())
        self.assertEqual(TransmissionEdge.objects.get(pk=edge.pk).sequence, 7)
        self.assertIsNone(TransmissionEdge.objects.get(pk=edge.pk).chain_index)
        migrated = client.get("/api/v1/hadiths/15/?chain=1").json()
        self.assertEqual(migrated["edges"], [expected])
        self.assertTrue(migrated["chain_index_available"])
        self.assertFalse(migrated["chain_boundaries_recorded"])

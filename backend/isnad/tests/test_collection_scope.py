import tempfile
from pathlib import Path

from django.core.cache import cache
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from isnad.management.commands.load_bukhari import Command, BUKHARI_ID
from isnad.models import Hadith, Narrator, TransmissionEdge
from isnad.serializers import HadithSerializer, TransmissionEdgeSerializer
from isnad.views import BOOKS_CACHE_KEY


class PublicCollectionScopeTests(APITestCase):
    def test_catalog_bootstrap_and_edges_exclude_non_bukhari_records(self):
        cache.delete(BOOKS_CACHE_KEY)
        self.addCleanup(cache.delete, BOOKS_CACHE_KEY)
        other = Hadith.objects.create(id=1, hadith_number="1", book_title="Sunan Abi Dawud", book_number=9)
        bukhari = Hadith.objects.create(id=2, hadith_number="1", book_title="Sahih al-Bukhari", book_number=1)
        teacher = Narrator.objects.create(id=1, name="Teacher")
        student = Narrator.objects.create(id=2, name="Student")
        excluded_student = Narrator.objects.create(id=3, name="Other collection student")
        foreign_edge = TransmissionEdge.objects.create(hadith=other, teacher=teacher, student=excluded_student, sequence=1)
        local_edges = [
            TransmissionEdge.objects.create(
                hadith=bukhari, teacher=teacher, student=student, sequence=1, chain_index=index,
            )
            for index in range(2)
        ]

        root = "/api/v1"
        result = self.client.get(f"{root}/hadiths/bootstrap/").json()
        self.assertEqual(result["hadith"]["id"], bukhari.id)
        self.assertEqual([book["number"] for book in result["books"]], [1])
        self.assertEqual([edge["chain_index"] for edge in result["edges"]], [0, 1])
        self.assertEqual(self.client.get(f"{root}/hadiths/1/?chain=1").json()["edges"], result["edges"])
        self.assertEqual(self.client.get(f"{root}/hadiths/").json()["count"], 1)
        self.assertEqual(self.client.get(f"{root}/edges/{foreign_edge.id}/").status_code, 404)
        self.assertEqual(self.client.get(f"{root}/edges/?hadith_id={other.id}").json()["count"], 0)
        self.assertEqual(self.client.get(f"{root}/edges/").json()["count"], len(local_edges))
        profile = self.client.get(f"{root}/narrators/{teacher.id}/").json()
        self.assertEqual([row["id"] for row in profile["transmission_students"]], [student.id])

    def test_write_validation_rejects_other_collection_and_conflicting_reference(self):
        for title, reference in [
            ("Sunan Abi Dawud", "https://sunnah.com/abudawud:832"),
            ("Sahih al-Bukhari", "https://sunnah.com/abudawud:832"),
        ]:
            serializer = HadithSerializer(data={"book_title": title, "reference_url": reference, "hadith_number": "832"})
            self.assertFalse(serializer.is_valid())
        other = Hadith(book_title="Sunan Abi Dawud")
        with self.assertRaisesMessage(ValidationError, "Only Sahih al-Bukhari is supported"):
            TransmissionEdgeSerializer().validate_hadith(other)

    def test_shuba_keeps_catalog_and_linked_scholarly_profile(self):
        narrator = Narrator.objects.create(id=20020, name="Shuʿba")
        response = self.client.get(f"/api/v1/narrators/{narrator.id}/").json()
        self.assertIn("muslimscholars.info", response["catalog_source_url"])
        self.assertEqual(response["knowledge_graph_profile"]["id"], 1003795)


class BukhariLoaderScopeTests(SimpleTestCase):
    def test_loader_rejects_other_collections_before_writing_hadiths(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-bukhari.csv"
            for line in (
                "Sunan Abi Dawud,https://sunnah.com/bukhari:832",
                "Sahih al-Bukhari,https://other.example/bukhari:832",
            ):
                path.write_text(f"Book,Reference\n{line}\n", encoding="utf-8")
                with self.assertRaisesMessage(CommandError, "Invalid Bukhari reference"):
                    Command().load_hadiths(path, {BUKHARI_ID: object()})

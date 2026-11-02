import shutil
import tempfile
from unittest import mock

import pymupdf
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from machines.models import Chunk, Machine, Manual

from . import vectorstore
from .llm import LLMUnavailable
from .models import Question, QuestionSource
from .services import (
    NOT_ENOUGH_MARKER,
    NOT_ENOUGH_MESSAGE,
    parse_citations,
    retrieve,
)

User = get_user_model()

# The simple "hash" embedder and an in-memory index keep these tests fast and
# free of downloads. The language model is replaced with a mock in each test.
TEST_SETTINGS = dict(
    RAG_EMBEDDING_BACKEND="hash",
    CHROMA_PATH=None,
    RAG_MIN_SCORE=0.30,
    RAG_TOP_K=4,
)

LASAGNA_QUESTION = "At what temperature should I bake the lasagna?"
SOURDOUGH_QUESTION = "How often do I feed the sourdough starter?"


def create_indexed_manual(machine, name, revision, pages):
    """Create a manual with the given (page, text) chunks and index it."""
    manual = Manual.objects.create(
        machine=machine,
        name=name,
        revision=revision,
        file=f"manuals/{name}.pdf",
    )
    Chunk.objects.bulk_create(
        Chunk(manual=manual, page_number=page, text=text) for page, text in pages
    )
    vectorstore.index_manual(manual)
    return manual


@override_settings(**TEST_SETTINGS)
class RetrievalTestCase(TestCase):
    """Shared data: three users and two machines with one manual each."""

    def setUp(self):
        vectorstore.reset_collection()
        self.client = APIClient()

        def make_user(username, role):
            user = User.objects.create_user(username=username, password="Pass@12345")
            group, _ = Group.objects.get_or_create(name=role)
            user.groups.add(group)
            return user

        self.engineer = make_user("engineer", "Engineer")
        self.admin = make_user("admin", "Administrator")
        self.supervisor = make_user("supervisor", "Supervisor")

        self.machine_a = Machine.objects.create(name="Kitchen A", model="Convection")
        self.machine_b = Machine.objects.create(name="Kitchen B", model="Deck")

        # Both machines mention lasagna with different values, on purpose.
        self.manual_a = create_indexed_manual(self.machine_a, "Oven A Manual", "1.0", [
            (1, "Lasagna. Bake the lasagna at 180 degrees Celsius for 45 minutes."),
            (2, "Maintenance. Replace the door gasket every 12 months."),
        ])
        self.manual_b = create_indexed_manual(self.machine_b, "Oven B Manual", "2.0", [
            (1, "Lasagna. Bake the lasagna at 200 degrees Celsius for 35 minutes."),
            (3, "Sourdough. Feed the sourdough starter every 12 hours with flour and water."),
        ])

    def ask(self, machine, question, user=None):
        self.client.force_authenticate(user=user or self.engineer)
        return self.client.post(
            "/api/ask/",
            {"machine": machine.id, "question": question},
            format="json",
        )


class WrongMachineTests(RetrievalTestCase):
    """Text from another machine must never be used."""

    def test_machine_b_only_question_retrieves_nothing_from_machine_b(self):
        b_chunk_ids = set(
            Chunk.objects.filter(manual__machine=self.machine_b)
            .values_list("id", flat=True)
        )

        # Machine B can answer this, which proves the test is meaningful.
        own_hits = retrieve(self.machine_b, SOURDOUGH_QUESTION)
        self.assertEqual(own_hits[0].page, 3)

        # Asked about machine A, no passage from machine B may come back.
        hits = retrieve(self.machine_a, SOURDOUGH_QUESTION)
        self.assertTrue(all(hit.machine_id == self.machine_a.id for hit in hits))
        self.assertEqual([hit for hit in hits if hit.chunk_id in b_chunk_ids], [])

    def test_question_for_other_machine_is_refused_without_calling_the_model(self):
        with mock.patch("retrieval.llm.generate") as fake_model:
            response = self.ask(self.machine_a, SOURDOUGH_QUESTION)

        fake_model.assert_not_called()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data["answered"])
        self.assertEqual(response.data["answer"], NOT_ENOUGH_MESSAGE)
        self.assertEqual(response.data["sources"], [])

    def test_database_check_drops_a_passage_from_the_wrong_machine(self):
        # Pretend the search index made a mistake and returned machine B's text.
        wrong_hits = vectorstore.search(self.machine_b.id, SOURDOUGH_QUESTION)

        with mock.patch("retrieval.vectorstore.search", return_value=wrong_hits):
            self.assertEqual(retrieve(self.machine_a, SOURDOUGH_QUESTION), [])

    def test_model_prompt_contains_only_the_selected_machines_text(self):
        with mock.patch("retrieval.llm.generate", return_value="180 degrees Celsius [1]") as fake_model:
            self.ask(self.machine_a, LASAGNA_QUESTION)

        prompt = fake_model.call_args[0][1]
        self.assertIn("180 degrees", prompt)
        self.assertNotIn("200 degrees", prompt)


class AskEndpointTests(RetrievalTestCase):

    def test_answered_question_is_saved_with_its_source(self):
        reply = "Bake at 180 degrees Celsius for 45 minutes [1]."
        with mock.patch("retrieval.llm.generate", return_value=reply):
            response = self.ask(self.machine_a, LASAGNA_QUESTION)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["answered"])

        source = response.data["sources"][0]
        self.assertEqual(source["manual_name"], "Oven A Manual")
        self.assertEqual(source["revision"], "1.0")
        self.assertEqual(source["page_number"], 1)
        self.assertEqual(source["pdf_url"], f"/api/manuals/{self.manual_a.id}/pdf/#page=1")

        saved = Question.objects.get(pk=response.data["id"])
        self.assertEqual(saved.user, self.engineer)
        self.assertEqual(saved.machine, self.machine_a)
        self.assertTrue(saved.answered)
        self.assertEqual(saved.sources.count(), 1)

    def test_model_can_report_that_the_answer_is_not_in_the_manual(self):
        with mock.patch("retrieval.llm.generate", return_value=NOT_ENOUGH_MARKER):
            response = self.ask(self.machine_a, LASAGNA_QUESTION)

        self.assertFalse(response.data["answered"])
        self.assertEqual(response.data["answer"], NOT_ENOUGH_MESSAGE)
        self.assertEqual(QuestionSource.objects.count(), 0)
        self.assertFalse(Question.objects.get().answered)

    def test_only_cited_passages_are_saved_as_sources(self):
        reply = "Replace the gasket every 12 months [1]."
        with mock.patch("retrieval.llm.generate", return_value=reply):
            response = self.ask(self.machine_a, "How often should the door gasket be replaced?")

        self.assertEqual([s["page_number"] for s in response.data["sources"]], [2])

    def test_only_engineers_can_ask_questions(self):
        with mock.patch("retrieval.llm.generate") as fake_model:
            for user in (self.admin, self.supervisor):
                response = self.ask(self.machine_a, LASAGNA_QUESTION, user=user)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            self.client.force_authenticate(user=None)
            anonymous = self.client.post(
                "/api/ask/",
                {"machine": self.machine_a.id, "question": "anything"},
                format="json",
            )
            self.assertIn(anonymous.status_code, (401, 403))

        fake_model.assert_not_called()
        self.assertEqual(Question.objects.count(), 0)

    def test_invalid_input_returns_a_clear_400(self):
        self.client.force_authenticate(user=self.engineer)
        bad_requests = [
            ({"machine": self.machine_a.id, "question": "   "}, "question"),
            ({"machine": self.machine_a.id}, "question"),
            ({"question": LASAGNA_QUESTION}, "machine"),
            ({"machine": 99999, "question": LASAGNA_QUESTION}, "machine"),
            ({"machine": self.machine_a.id, "question": "x" * 1001}, "question"),
        ]

        with mock.patch("retrieval.llm.generate") as fake_model:
            for body, field in bad_requests:
                response = self.client.post("/api/ask/", body, format="json")
                self.assertEqual(response.status_code, 400, body)
                self.assertIn(field, response.data)

        fake_model.assert_not_called()

    def test_model_outage_returns_503_and_saves_nothing(self):
        with mock.patch("retrieval.llm.generate", side_effect=LLMUnavailable("service down")):
            response = self.ask(self.machine_a, LASAGNA_QUESTION)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["detail"], "service down")
        self.assertEqual(Question.objects.count(), 0)


class IndexingTests(RetrievalTestCase):

    def test_parse_citations(self):
        self.assertEqual(parse_citations("See [2], then [1], then [2] and [9]", 3), [1, 2])
        self.assertEqual(parse_citations("No citations here", 3), [])

    def test_deleting_a_manual_removes_it_from_search(self):
        self.manual_b.delete()
        self.assertEqual(vectorstore.search(self.machine_b.id, SOURDOUGH_QUESTION), [])

    def test_history_stays_readable_after_a_manual_is_deleted(self):
        with mock.patch("retrieval.llm.generate", return_value="180 degrees [1]"):
            question_id = self.ask(self.machine_a, LASAGNA_QUESTION).data["id"]

        self.manual_a.delete()

        source = QuestionSource.objects.get(question_id=question_id)
        self.assertIsNone(source.manual_id)
        self.assertEqual(source.manual_name, "Oven A Manual")
        self.assertIn("180 degrees", source.text)

    def test_uploading_a_pdf_makes_it_searchable_with_correct_pages(self):
        temp_media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_media, True)

        pdf = pymupdf.open()
        pdf.new_page().insert_text((72, 72), "Introduction to the planetary gearbox overview")
        pdf.new_page().insert_text((72, 72), "Torque wrench setting for gearbox bolts is 45 Nm")
        pdf_bytes = pdf.tobytes()
        pdf.close()

        self.client.force_authenticate(user=self.admin)
        with override_settings(MEDIA_ROOT=temp_media):
            response = self.client.post(
                "/api/manuals/upload/",
                {
                    "machine_name": "Gearbox",
                    "machine_model": "G1",
                    "name": "Gearbox Manual",
                    "revision": "A",
                    "file": SimpleUploadedFile("gearbox.pdf", pdf_bytes, content_type="application/pdf"),
                },
                format="multipart",
            )
        self.assertEqual(response.status_code, 201, response.data)

        hits = vectorstore.search(
            response.data["machine_id"],
            "What is the torque wrench setting for gearbox bolts?",
        )
        self.assertEqual(hits[0].page, 2)
        self.assertEqual(hits[0].revision, "A")

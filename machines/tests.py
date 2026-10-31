
import os
import shutil
import tempfile

import pymupdf

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import IntegrityError
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from .models import Chunk, Machine, Manual
from .services import split_text_into_chunks


User = get_user_model()


class MachineModelTests(TestCase):

    def test_machine_creation(self):
        machine = Machine.objects.create(
            name="CNC Milling Machine",
            model="VF-2"
        )
        self.assertEqual(str(machine), "CNC Milling Machine (VF-2)")
        self.assertEqual(machine.name, "CNC Milling Machine")
        self.assertEqual(machine.model, "VF-2")

    def test_machine_unique_together(self):
        Machine.objects.create(name="Haas Mill", model="VF-2")

        with self.assertRaises(IntegrityError):
            Machine.objects.create(name="Haas Mill", model="VF-2")


class ManualModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="test_admin",
            password="TestPassword@123",
        )
        self.machine = Machine.objects.create(
            name="Haas Lathe",
            model="ST-10"
        )

    def test_manual_creation(self):
        manual = Manual.objects.create(
            machine=self.machine,
            name="ST-10 Operator Manual",
            revision="1.0",
            file="manuals/st10.pdf",
            uploaded_by=self.user,
        )

        self.assertEqual(str(manual), "ST-10 Operator Manual (Rev 1.0)")
        self.assertEqual(manual.machine, self.machine)
        self.assertEqual(manual.uploaded_by, self.user)
        self.assertIsNotNone(manual.uploaded_at)
        self.assertEqual(manual.file.name, "manuals/st10.pdf")

    def test_manual_reverse_relations(self):
        manual = Manual.objects.create(
            machine=self.machine,
            name="ST-10 Service Manual",
            revision="1.0",
            file="manuals/st10_service.pdf",
            uploaded_by=self.user,
        )

        self.assertIn(manual, self.machine.manuals.all())
        self.assertIn(manual, self.user.uploaded_manuals.all())

    def test_user_deletion_sets_null(self):
        manual = Manual.objects.create(
            machine=self.machine,
            name="Maintenance Guide",
            revision="A",
            file="manuals/guide.pdf",
            uploaded_by=self.user,
        )

        self.user.delete()
        manual.refresh_from_db()

        self.assertIsNone(manual.uploaded_by)

    def test_machine_deletion_cascades_to_manual(self):
        manual = Manual.objects.create(
            machine=self.machine,
            name="Quick Reference",
            revision="B",
            file="manuals/ref.pdf",
            uploaded_by=self.user,
        )

        manual_id = manual.id
        self.machine.delete()

        self.assertFalse(Manual.objects.filter(id=manual_id).exists())


class ChunkModelTests(TestCase):

    def setUp(self):
        self.machine = Machine.objects.create(
            name="Haas Drill",
            model="DT-1"
        )
        self.manual = Manual.objects.create(
            machine=self.machine,
            name="DT-1 User Guide",
            revision="1.0",
            file="manuals/dt1.pdf",
        )

    def test_chunk_creation(self):
        chunk = Chunk.objects.create(
            manual=self.manual,
            page_number=1,
            text="Chapter 1: Safety instructions.",
        )

        self.assertEqual(chunk.manual, self.manual)
        self.assertEqual(chunk.page_number, 1)
        self.assertEqual(chunk.text, "Chapter 1: Safety instructions.")
        self.assertIn(chunk, self.manual.chunks.all())

    def test_page_number_minimum_validation(self):
        chunk = Chunk(
            manual=self.manual,
            page_number=0,
            text="Invalid zero page",
        )

        with self.assertRaises(ValidationError):
            chunk.full_clean()

    def test_manual_deletion_cascades_to_chunk(self):
        chunk = Chunk.objects.create(
            manual=self.manual,
            page_number=5,
            text="Page 5 content",
        )

        chunk_id = chunk.id
        self.manual.delete()

        self.assertFalse(Chunk.objects.filter(id=chunk_id).exists())


class ManualUploadAPITests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp_media = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_media, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/manuals/upload/"

        self.admin_group, _ = Group.objects.get_or_create(
            name="Administrator"
        )
        self.engineer_group, _ = Group.objects.get_or_create(
            name="Engineer"
        )
        self.supervisor_group, _ = Group.objects.get_or_create(
            name="Supervisor"
        )

        self.admin_user = User.objects.create_user(
            username="admin_uploader",
            password="AdminPassword@123",
        )
        self.admin_user.groups.add(self.admin_group)

        self.engineer_user = User.objects.create_user(
            username="engineer_user",
            password="EngineerPassword@123",
        )
        self.engineer_user.groups.add(self.engineer_group)

        self.supervisor_user = User.objects.create_user(
            username="supervisor_user",
            password="SupervisorPassword@123",
        )
        self.supervisor_user.groups.add(self.supervisor_group)

    def _create_valid_pdf_file(self, filename="valid_manual.pdf"):
        pdf = pymupdf.open()
        page = pdf.new_page()
        page.insert_text(
            (72, 72),
            "This is valid test content for PDF extraction.",
        )

        content = pdf.tobytes()
        pdf.close()

        return SimpleUploadedFile(
            filename,
            content,
            content_type="application/pdf",
        )

    def test_admin_successful_upload(self):
        self.client.force_authenticate(user=self.admin_user)
        pdf_file = self._create_valid_pdf_file("vf2_manual.pdf")

        data = {
            "machine_name": "Haas Mill",
            "machine_model": "VF-2",
            "name": "VF-2 Operator Manual",
            "revision": "1.0",
            "file": pdf_file,
        }

        with override_settings(MEDIA_ROOT=self.temp_media):
            response = self.client.post(
                self.url, data, format="multipart"
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["name"], "VF-2 Operator Manual")
        self.assertEqual(response.data["revision"], "1.0")
        self.assertEqual(response.data["machine_name"], "Haas Mill")
        self.assertEqual(response.data["machine_model"], "VF-2")
        self.assertIn("machine_id", response.data)
        self.assertIn("uploaded_at", response.data)
        self.assertNotIn("file", response.data)
        self.assertNotIn("file_url", response.data)

        machine = Machine.objects.get(name="Haas Mill", model="VF-2")
        manual = Manual.objects.get(id=response.data["id"])

        self.assertEqual(manual.machine, machine)
        self.assertEqual(manual.uploaded_by, self.admin_user)

    def test_upload_reuses_existing_machine(self):
        existing_machine = Machine.objects.create(
            name="Haas Lathe",
            model="ST-10"
        )

        self.client.force_authenticate(user=self.admin_user)
        pdf_file = self._create_valid_pdf_file("st10_manual.pdf")

        data = {
            "machine_name": "Haas Lathe",
            "machine_model": "ST-10",
            "name": "ST-10 Maintenance Guide",
            "revision": "2.0",
            "file": pdf_file,
        }

        with override_settings(MEDIA_ROOT=self.temp_media):
            response = self.client.post(
                self.url, data, format="multipart"
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["machine_id"], existing_machine.id)
        self.assertEqual(
            Machine.objects.filter(
                name="Haas Lathe",
                model="ST-10"
            ).count(),
            1,
        )

    def test_unauthenticated_request_rejected(self):
        pdf_file = self._create_valid_pdf_file()

        data = {
            "machine_name": "Haas Mill",
            "machine_model": "VF-2",
            "name": "Manual",
            "revision": "1.0",
            "file": pdf_file,
        }

        response = self.client.post(self.url, data, format="multipart")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )

    def test_engineer_access_forbidden(self):
        self.client.force_authenticate(user=self.engineer_user)
        pdf_file = self._create_valid_pdf_file()

        data = {
            "machine_name": "Haas Mill",
            "machine_model": "VF-2",
            "name": "Manual",
            "revision": "1.0",
            "file": pdf_file,
        }

        response = self.client.post(self.url, data, format="multipart")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )

    def test_duplicate_manual_revision(self):
        self.client.force_authenticate(user=self.admin_user)
        pdf_file = self._create_valid_pdf_file("dup_manual.pdf")

        data = {
            "machine_name": "Haas Mill",
            "machine_model": "VF-2",
            "name": "VF-2 Operator Manual",
            "revision": "1.0",
            "file": pdf_file,
        }

        with override_settings(MEDIA_ROOT=self.temp_media):
            response1 = self.client.post(
                self.url, data, format="multipart"
            )

        self.assertEqual(
            response1.status_code,
            status.HTTP_201_CREATED
        )

        pdf_file2 = self._create_valid_pdf_file("dup_manual2.pdf")
        data2 = data.copy()
        data2["file"] = pdf_file2

        with override_settings(MEDIA_ROOT=self.temp_media):
            response2 = self.client.post(
                self.url, data2, format="multipart"
            )

        self.assertEqual(
            response2.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("non_field_errors", response2.data)
        self.assertIn(
            "A manual with this revision already exists for this machine.",
            str(response2.data),
        )

        self.client.force_authenticate(user=self.supervisor_user)
        pdf_file = self._create_valid_pdf_file()

        data = {
            "machine_name": "Haas Mill",
            "machine_model": "VF-2",
            "name": "Manual",
            "revision": "1.0",
            "file": pdf_file,
        }

        response = self.client.post(self.url, data, format="multipart")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )

    def test_reject_non_pdf_extension(self):
        self.client.force_authenticate(user=self.admin_user)

        txt_file = SimpleUploadedFile(
            "manual.txt",
            b"%PDF-1.4 text content",
            content_type="text/plain",
        )

        data = {
            "machine_name": "Haas Mill",
            "machine_model": "VF-2",
            "name": "Manual",
            "revision": "1.0",
            "file": txt_file,
        }

        with override_settings(MEDIA_ROOT=self.temp_media):
            response = self.client.post(
                self.url, data, format="multipart"
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("file", response.data)
        self.assertTrue(
            any(".pdf" in str(err).lower() for err in response.data["file"])
        )

    def test_reject_invalid_pdf_magic_bytes(self):
        self.client.force_authenticate(user=self.admin_user)

        fake_pdf = SimpleUploadedFile(
            "fake.pdf",
            b"NOT_A_PDF_DOCUMENT_CONTENT",
            content_type="application/pdf",
        )

        data = {
            "machine_name": "Haas Mill",
            "machine_model": "VF-2",
            "name": "Manual",
            "revision": "1.0",
            "file": fake_pdf,
        }

        with override_settings(MEDIA_ROOT=self.temp_media):
            response = self.client.post(
                self.url, data, format="multipart"
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("file", response.data)

    def test_reject_empty_file(self):
        self.client.force_authenticate(user=self.admin_user)

        empty_file = SimpleUploadedFile(
            "empty.pdf",
            b"",
            content_type="application/pdf",
        )

        data = {
            "machine_name": "Haas Mill",
            "machine_model": "VF-2",
            "name": "Manual",
            "revision": "1.0",
            "file": empty_file,
        }

        with override_settings(MEDIA_ROOT=self.temp_media):
            response = self.client.post(
                self.url, data, format="multipart"
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("file", response.data)

    def test_reject_oversized_file(self):
        self.client.force_authenticate(user=self.admin_user)

        oversized_content = b"%PDF-" + (
            b"X" * (25 * 1024 * 1024 + 10)
        )

        oversized_file = SimpleUploadedFile(
            "large.pdf",
            oversized_content,
            content_type="application/pdf",
        )

        data = {
            "machine_name": "Haas Mill",
            "machine_model": "VF-2",
            "name": "Manual",
            "revision": "1.0",
            "file": oversized_file,
        }

        with override_settings(MEDIA_ROOT=self.temp_media):
            response = self.client.post(
                self.url, data, format="multipart"
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("file", response.data)
        self.assertTrue(
            any(
                "25 mb" in str(err).lower()
                for err in response.data["file"]
            )
        )

    # TASK 5 TESTS

    def test_reject_corrupted_pdf_with_valid_header(self):
        self.client.force_authenticate(user=self.admin_user)

        corrupted_pdf = SimpleUploadedFile(
            "corrupted.pdf",
            b"%PDF-1.4 this is not a real PDF document",
            content_type="application/pdf",
        )

        data = {
            "machine_name": "Haas Mill",
            "machine_model": "VF-2",
            "name": "Corrupted Manual",
            "revision": "1.0",
            "file": corrupted_pdf,
        }

        with override_settings(MEDIA_ROOT=self.temp_media):
            response = self.client.post(
                self.url, data, format="multipart"
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("file", response.data)
        self.assertFalse(
            Manual.objects.filter(
                name="Corrupted Manual",
                revision="1.0"
            ).exists()
        )

    def test_reject_pdf_without_extractable_text(self):
        self.client.force_authenticate(user=self.admin_user)

        pdf = pymupdf.open()
        page = pdf.new_page()

        pixmap = pymupdf.Pixmap(
            pymupdf.csRGB,
            pymupdf.IRect(0, 0, 100, 100),
            0
        )
        pixmap.clear_with(255)

        image_bytes = pixmap.tobytes("png")
        page.insert_image(page.rect, stream=image_bytes)

        pdf_content = pdf.tobytes()
        pdf.close()

        image_only_pdf = SimpleUploadedFile(
            "scanned_manual.pdf",
            pdf_content,
            content_type="application/pdf",
        )

        data = {
            "machine_name": "Haas Mill",
            "machine_model": "VF-2",
            "name": "Scanned Manual",
            "revision": "1.0",
            "file": image_only_pdf,
        }

        with override_settings(MEDIA_ROOT=self.temp_media):
            response = self.client.post(
                self.url, data, format="multipart"
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("file", response.data)
        self.assertFalse(
            Manual.objects.filter(
                name="Scanned Manual",
                revision="1.0"
            ).exists()
        )

    def test_failed_extraction_cleans_up_manual_and_file(self):
        self.client.force_authenticate(user=self.admin_user)

        existing_files = set(os.listdir(self.temp_media))

        corrupted_pdf = SimpleUploadedFile(
            "cleanup_test.pdf",
            b"%PDF-1.4 invalid PDF content",
            content_type="application/pdf",
        )

        data = {
            "machine_name": "Haas Mill",
            "machine_model": "VF-2",
            "name": "Cleanup Test Manual",
            "revision": "1.0",
            "file": corrupted_pdf,
        }

        with override_settings(MEDIA_ROOT=self.temp_media):
            response = self.client.post(
                self.url, data, format="multipart"
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertFalse(
            Manual.objects.filter(
                name="Cleanup Test Manual",
                revision="1.0"
            ).exists()
        )
        self.assertEqual(
            set(os.listdir(self.temp_media)),
            existing_files
        )


class TextChunkingTests(TestCase):

    def test_chunk_size_is_within_limit(self):
        text = " ".join(f"word{i}" for i in range(450))
        chunks = split_text_into_chunks(text)

        self.assertGreater(len(chunks), 1)

        for chunk in chunks:
            self.assertLessEqual(len(chunk.split()), 250)

    def test_chunks_have_30_word_overlap(self):
        text = " ".join(f"word{i}" for i in range(450))
        chunks = split_text_into_chunks(text)

        self.assertGreaterEqual(len(chunks), 2)

        first_words = chunks[0].split()
        second_words = chunks[1].split()

        self.assertEqual(first_words[-30:], second_words[:30])

    def test_empty_text_returns_empty_list(self):
        self.assertEqual(split_text_into_chunks(""), [])

    def test_short_text_returns_one_chunk(self):
        text = "This is a short test."
        chunks = split_text_into_chunks(text)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_overlap_must_be_smaller_than_chunk_size(self):
        with self.assertRaises(ValueError):
            split_text_into_chunks(
                "sample text",
                chunk_size=10,
                overlap=10
            )


# TASK 6 TESTS

class ManualPDFViewAPITests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp_media = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_media, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/manuals/"

        self.admin_group, _ = Group.objects.get_or_create(
            name="Administrator"
        )
        self.engineer_group, _ = Group.objects.get_or_create(
            name="Engineer"
        )
        self.supervisor_group, _ = Group.objects.get_or_create(
            name="Supervisor"
        )

        self.admin_user = User.objects.create_user(
            username="pdf_admin",
            password="AdminPassword@123",
        )
        self.admin_user.groups.add(self.admin_group)

        self.engineer_user = User.objects.create_user(
            username="pdf_engineer",
            password="EngineerPassword@123",
        )
        self.engineer_user.groups.add(self.engineer_group)

        self.supervisor_user = User.objects.create_user(
            username="pdf_supervisor",
            password="SupervisorPassword@123",
        )
        self.supervisor_user.groups.add(self.supervisor_group)

        self.machine = Machine.objects.create(
            name="Haas Mill",
            model="VF-2",
        )

    def _create_manual(self):
        pdf = pymupdf.open()
        page = pdf.new_page()
        page.insert_text(
            (72, 72),
            "This is a protected PDF manual.",
        )

        pdf_content = pdf.tobytes()
        pdf.close()

        uploaded_file = SimpleUploadedFile(
            "protected_manual.pdf",
            pdf_content,
            content_type="application/pdf",
        )

        # Save the PDF using the same temporary MEDIA_ROOT
        # that the endpoint uses to retrieve the file.
        with override_settings(MEDIA_ROOT=self.temp_media):
            manual = Manual.objects.create(
                machine=self.machine,
                name="Protected Manual",
                revision="1.0",
                file=uploaded_file,
            )

        return manual

    def test_administrator_can_view_manual_pdf(self):
        self.client.force_authenticate(user=self.admin_user)
        manual = self._create_manual()

        with override_settings(MEDIA_ROOT=self.temp_media):
            response = self.client.get(
                f"{self.url}{manual.id}/pdf/"
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("inline", response["Content-Disposition"])

    def test_engineer_can_view_manual_pdf(self):
        self.client.force_authenticate(user=self.engineer_user)
        manual = self._create_manual()

        with override_settings(MEDIA_ROOT=self.temp_media):
            response = self.client.get(
                f"{self.url}{manual.id}/pdf/"
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("inline", response["Content-Disposition"])
        self.assertEqual(
            b"".join(response.streaming_content)[:5],
            b"%PDF-",
        )

    def test_supervisor_can_view_manual_pdf(self):
        self.client.force_authenticate(user=self.supervisor_user)
        manual = self._create_manual()

        with override_settings(MEDIA_ROOT=self.temp_media):
            response = self.client.get(
                f"{self.url}{manual.id}/pdf/"
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_unauthenticated_user_cannot_view_manual_pdf(self):
        manual = self._create_manual()

        with override_settings(MEDIA_ROOT=self.temp_media):
            response = self.client.get(
                f"{self.url}{manual.id}/pdf/"
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_nonexistent_manual_returns_404(self):
        self.client.force_authenticate(user=self.engineer_user)

        with override_settings(MEDIA_ROOT=self.temp_media):
            response = self.client.get(
                f"{self.url}99999/pdf/"
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_missing_pdf_file_returns_404(self):
        self.client.force_authenticate(user=self.engineer_user)

        with override_settings(MEDIA_ROOT=self.temp_media):
            manual = Manual.objects.create(
                machine=self.machine,
                name="Missing File Manual",
                revision="1.0",
                file="manuals/missing_file.pdf",
            )

            response = self.client.get(
                f"{self.url}{manual.id}/pdf/"
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

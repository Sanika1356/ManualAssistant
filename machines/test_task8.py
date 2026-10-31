
import shutil
import tempfile

import pymupdf

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from rest_framework import status
from rest_framework.test import APIClient

from .models import Chunk


User = get_user_model()


class ThreePagePDFExtractionTests(TestCase):

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

        admin_group, _ = Group.objects.get_or_create(
            name="Administrator"
        )

        self.admin_user = User.objects.create_user(
            username="task8_admin",
            password="AdminPassword@123",
        )
        self.admin_user.groups.add(admin_group)

        self.client.force_authenticate(user=self.admin_user)

    def _create_three_page_pdf(self):
        pdf = pymupdf.open()

        page_texts = [
            "This is the unique content of PDF page one.",
            "This is the unique content of PDF page two.",
            "This is the unique content of PDF page three.",
        ]

        for text in page_texts:
            page = pdf.new_page()
            page.insert_text((72, 72), text)

        pdf_content = pdf.tobytes()
        pdf.close()

        return SimpleUploadedFile(
            "three_page_manual.pdf",
            pdf_content,
            content_type="application/pdf",
        )

    def test_three_page_pdf_preserves_page_numbers(self):
        pdf_file = self._create_three_page_pdf()

        upload_data = {
            "machine_name": "Task Eight Test Machine",
            "machine_model": "T8-100",
            "name": "Three Page Test Manual",
            "revision": "1.0",
            "file": pdf_file,
        }

        with override_settings(MEDIA_ROOT=self.temp_media):
            response = self.client.post(
                "/api/manuals/upload/",
                upload_data,
                format="multipart",
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
            )

            manual_id = response.data["id"]

            chunks = list(
                Chunk.objects.filter(
                    manual_id=manual_id
                ).order_by("page_number")
            )

        self.assertEqual(len(chunks), 3)

        self.assertEqual(
            [chunk.page_number for chunk in chunks],
            [1, 2, 3],
        )

        self.assertIn(
            "page one",
            chunks[0].text.lower(),
        )

        self.assertIn(
            "page two",
            chunks[1].text.lower(),
        )

        self.assertIn(
            "page three",
            chunks[2].text.lower(),
        )

        self.assertEqual(
            chunks[1].page_number,
            2,
        )

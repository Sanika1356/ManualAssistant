import pymupdf

from django.db import transaction

from .models import Chunk, Manual


def extract_pdf_text(manual):
    """
    Extract text from each PDF page and save it
    as a Chunk with the correct 1-indexed page number.
    """

    extracted_chunks = []

    try:
        with pymupdf.open(manual.file.path) as pdf:

            if pdf.page_count == 0:
                raise ValueError("The uploaded PDF has no pages.")

            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text").strip()

                if text:
                    extracted_chunks.append(
                        Chunk(
                            manual=manual,
                            page_number=page_number,
                            text=text
                        )
                    )

            if not extracted_chunks:
                raise ValueError(
                    "No extractable text found in the uploaded PDF."
                )

    except (pymupdf.FileDataError, RuntimeError, OSError) as error:
        raise ValueError(
            "The uploaded PDF is corrupted or unreadable."
        ) from error

    with transaction.atomic():
        Chunk.objects.filter(manual=manual).delete()
        Chunk.objects.bulk_create(extracted_chunks)

    return len(extracted_chunks)
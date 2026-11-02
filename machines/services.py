import pymupdf

from django.db import transaction

from .models import Chunk, Manual


CHUNK_SIZE = 250
CHUNK_OVERLAP = 30


def split_text_into_chunks(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Split text into word-based chunks.
    Default: 250 words per chunk with 30 words overlap.
    """

    words = text.split()

    if not words:
        return []

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("Chunk overlap must be smaller than chunk size.")

    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))

        chunks.append(" ".join(words[start:end]))

        if end == len(words):
            break

        start = end - overlap

    return chunks


def build_page_header(manual, page_number):
    """First line of a chunk, for example HP-OPS-01 | M-HP200 | Rev 1.0 | Page 2."""
    parts = [
        manual.document_id or manual.name,
        manual.machine.machine_code,
        f"Rev {manual.revision}",
        f"Page {page_number}",
    ]
    return " | ".join(part for part in parts if part)


def extract_pdf_text(manual):
    """
    Extract PDF text page-by-page and save one chunk per page.

    Keeping each page whole means a key sentence is never cut away from the
    rest of its page, and every chunk maps to exactly one PDF page. The first
    line of each chunk says which document and page it came from.
    """

    extracted_chunks = []

    try:
        with manual.file.open("rb") as uploaded_pdf:
            pdf_content = uploaded_pdf.read()

        with pymupdf.open(stream=pdf_content, filetype="pdf") as pdf:

            if pdf.page_count == 0:
                raise ValueError("The uploaded PDF has no pages.")

            for page_number, page in enumerate(pdf, start=1):
                page_text = page.get_text("text").strip()

                if not page_text:
                    continue

                # Tidy line breaks and repeated spaces from the PDF.
                page_text = " ".join(page_text.split())

                extracted_chunks.append(
                    Chunk(
                        manual=manual,
                        page_number=page_number,
                        text=f"{build_page_header(manual, page_number)}\n{page_text}",
                    )
                )

            if not extracted_chunks:
                raise ValueError(
                    "No extractable text found in the uploaded PDF."
                )

    except ValueError:
        raise

    except (pymupdf.FileDataError, RuntimeError, OSError) as error:
        raise ValueError(
            "The uploaded PDF is corrupted or unreadable."
        ) from error

    with transaction.atomic():
        Chunk.objects.filter(manual=manual).delete()
        Chunk.objects.bulk_create(extracted_chunks)

    return len(extracted_chunks)
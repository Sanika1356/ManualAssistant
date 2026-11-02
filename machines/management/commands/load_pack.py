"""
Loads the machines and manuals listed in the organisers' student pack.

    python manage.py load_pack "C:\\path\\to\\Student_Pack"

The folder must hold machine_manual_index.csv and a Manuals folder with the PDFs.
It is safe to run again: existing records are reused, never duplicated, and
each manual's text and search entries are rebuilt from its stored PDF.
"""
import csv
import re
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from machines.models import Chunk, Machine, Manual
from machines.services import extract_pdf_text
from retrieval.vectorstore import index_manual

CSV_NAME = "machine_manual_index.csv"
PDF_FOLDER = "Manuals"
REQUIRED_COLUMNS = {
    "machine_id", "model", "machine_name", "document_id", "revision", "pdf_filename",
}


def manual_name_from(document_id, pdf_filename):
    """HP-OPS-01 and HP200_Operations_Rev1_0.pdf give "HP-OPS-01 Operations"."""
    stem = re.sub(r"_Rev.*$", "", Path(pdf_filename).stem, flags=re.IGNORECASE)
    words = stem.split("_")[1:]
    return f"{document_id} {' and '.join(words)}".strip()


def read_rows(csv_path):
    """Read the CSV. newline="" lets the csv module handle Windows line endings."""
    with open(csv_path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = {name.strip() for name in reader.fieldnames or []}

        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise CommandError(f"{CSV_NAME} is missing: {', '.join(sorted(missing))}")

        return [
            {key.strip(): (value or "").strip() for key, value in row.items() if key}
            for row in reader
            if any((value or "").strip() for value in row.values() if isinstance(value, str))
        ]


def get_machine(row):
    """Find the machine by ID, then by name and model, otherwise create it."""
    machine = Machine.objects.filter(machine_code=row["machine_id"]).first()
    if machine is None:
        machine = Machine.objects.filter(
            name=row["machine_name"], model=row["model"]
        ).first()
    if machine is None:
        return Machine.objects.create(
            machine_code=row["machine_id"],
            name=row["machine_name"],
            model=row["model"],
        ), True

    machine.machine_code = row["machine_id"]
    machine.name = row["machine_name"]
    machine.model = row["model"]
    machine.save()
    return machine, False


class Command(BaseCommand):
    help = "Load the student pack's machines and manuals in one step."

    def add_arguments(self, parser):
        parser.add_argument("pack_folder", help="Folder holding the CSV and the Manuals folder.")

    def handle(self, *args, **options):
        pack = Path(options["pack_folder"])
        csv_path = pack / CSV_NAME
        if not csv_path.is_file():
            raise CommandError(f"Could not find {csv_path}")

        rows = read_rows(csv_path)
        if not rows:
            raise CommandError(f"{CSV_NAME} has no rows.")

        # Check every PDF first, so a missing file changes nothing.
        pdf_paths = {row["pdf_filename"]: pack / PDF_FOLDER / row["pdf_filename"] for row in rows}
        missing = [str(path) for path in pdf_paths.values() if not path.is_file()]
        if missing:
            raise CommandError("Could not find: " + ", ".join(missing))

        for row in rows:
            machine, machine_created = get_machine(row)
            if machine_created:
                self.stdout.write(f"Machine added: {machine.machine_code}")

            manual = Manual.objects.filter(
                document_id=row["document_id"], revision=row["revision"]
            ).first()
            created = manual is None

            if manual is None:
                with open(pdf_paths[row["pdf_filename"]], "rb") as pdf:
                    manual = Manual.objects.create(
                        machine=machine,
                        name=manual_name_from(row["document_id"], row["pdf_filename"]),
                        revision=row["revision"],
                        document_id=row["document_id"],
                        file=File(pdf, name=row["pdf_filename"]),
                    )

            try:
                extract_pdf_text(manual)
                index_manual(manual)
            except Exception as error:
                if created:
                    manual.file.delete(save=False)
                    manual.delete()
                raise CommandError(f"{row['document_id']} failed: {error}")

            self.stdout.write(
                f"{'Added' if created else 'Refreshed'}: {manual.document_id} "
                f"Rev {manual.revision}, "
                f"{Chunk.objects.filter(manual=manual).count()} chunks"
            )

        ids = {row["document_id"] for row in rows}
        pages = (
            Chunk.objects.filter(manual__document_id__in=ids)
            .values("manual_id", "page_number").distinct().count()
        )
        machines = len({row["machine_id"] for row in rows})
        self.stdout.write(self.style.SUCCESS(
            f"Done: {machines} machines, {len(rows)} manuals, {pages} pages."
        ))
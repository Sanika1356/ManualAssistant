from django.core.management.base import BaseCommand

from machines.models import Manual
from retrieval import vectorstore


class Command(BaseCommand):
    help = (
        "Rebuild the search index from the saved chunks. "
        "Run this after cloning the project or restoring a database."
    )

    def handle(self, *args, **options):
        vectorstore.reset_collection()

        total = 0
        for manual in Manual.objects.select_related("machine"):
            count = vectorstore.index_manual(manual)
            total += count
            self.stdout.write(
                f"  {manual.machine} | {manual.name} (rev {manual.revision}): {count} chunks"
            )

        self.stdout.write(self.style.SUCCESS(f"Indexed {total} chunks."))

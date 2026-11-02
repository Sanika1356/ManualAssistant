from django.db.models.signals import post_delete
from django.dispatch import receiver

from machines.models import Manual

from . import vectorstore


@receiver(post_delete, sender=Manual)
def remove_manual_from_search(sender, instance, **kwargs):
    """Deleting a manual (or its machine) also removes it from the search index."""
    try:
        vectorstore.remove_manual(instance.id)
    except Exception:
        # A search index problem should never stop a manual from being deleted.
        # "python manage.py reindex" rebuilds the index from the database.
        pass

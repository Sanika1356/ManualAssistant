from django.apps import AppConfig


class RetrievalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "retrieval"

    def ready(self):
        # Importing the signals module is what registers the receivers.
        from . import signals  # noqa: F401

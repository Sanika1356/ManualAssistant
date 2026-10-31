
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Machine(models.Model):
    name = models.CharField(max_length=255)
    model = models.CharField(max_length=255)

    class Meta:
        unique_together = ('name', 'model')
        ordering = ['name', 'model']

    def __str__(self):
        return f"{self.name} ({self.model})"


class Manual(models.Model):
    machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE,
        related_name='manuals',
    )
    name = models.CharField(max_length=255)
    revision = models.CharField(max_length=100)
    file = models.FileField(upload_to='manuals/')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_manuals',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        constraints = [
            models.UniqueConstraint(
                fields=['machine', 'name', 'revision'],
                name='unique_manual_revision_per_machine',
            ),
        ]

    def __str__(self):
        return f"{self.name} (Rev {self.revision})"


class Chunk(models.Model):
    manual = models.ForeignKey(
        Manual,
        on_delete=models.CASCADE,
        related_name='chunks',
    )
    page_number = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="1-indexed page number",
    )
    text = models.TextField()

    class Meta:
        ordering = ['page_number']

    def __str__(self):
        return f"Manual {self.manual_id} - Page {self.page_number}"

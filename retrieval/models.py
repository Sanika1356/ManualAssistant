from django.conf import settings
from django.db import models

from machines.models import Chunk, Machine, Manual


class Question(models.Model):
    """A question asked by an Engineer, together with the saved answer."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    text = models.TextField()
    answer = models.TextField(blank=True)
    # False means the manuals did not contain enough information.
    answered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        state = "answered" if self.answered else "no answer"
        return f"Question {self.pk} ({state}): {self.text[:50]}"


class QuestionSource(models.Model):
    """
    A manual passage that was used to answer a question.

    The chunk and manual links can become empty if the manual is deleted
    later, so the passage details are also copied into this row. That keeps
    the question history readable after a manual is removed.
    """

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="sources",
    )
    chunk = models.ForeignKey(
        Chunk,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    manual = models.ForeignKey(
        Manual,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    # The number used to cite this passage in the answer, for example [1].
    passage_number = models.PositiveIntegerField()
    manual_name = models.CharField(max_length=255)
    revision = models.CharField(max_length=100)
    page_number = models.PositiveIntegerField()
    text = models.TextField()
    score = models.FloatField()

    class Meta:
        ordering = ["passage_number"]

    def __str__(self):
        return (
            f"Question {self.question_id}, passage {self.passage_number}: "
            f"{self.manual_name} page {self.page_number}"
        )

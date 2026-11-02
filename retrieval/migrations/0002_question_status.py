from django.db import migrations, models


def copy_answered_to_status(apps, schema_editor):
    """Give questions saved before this change the matching status."""
    Question = apps.get_model("retrieval", "Question")
    Question.objects.filter(answered=True).update(status="answered")
    Question.objects.filter(answered=False).update(status="insufficient_evidence")


def copy_status_to_answered(apps, schema_editor):
    """Undo the change: rebuild the old yes/no field from status."""
    Question = apps.get_model("retrieval", "Question")
    Question.objects.filter(status="answered").update(answered=True)
    Question.objects.exclude(status="answered").update(answered=False)


class Migration(migrations.Migration):

    dependencies = [
        ("retrieval", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="status",
            field=models.CharField(
                choices=[
                    ("answered", "Answered"),
                    ("insufficient_evidence", "Insufficient evidence"),
                ],
                default="insufficient_evidence",
                max_length=30,
            ),
        ),
        migrations.RunPython(copy_answered_to_status, copy_status_to_answered),
        migrations.RemoveField(
            model_name="question",
            name="answered",
        ),
    ]

from rest_framework import serializers

from machines.models import Machine

from .models import Question, QuestionSource


class AskRequestSerializer(serializers.Serializer):
    machine = serializers.PrimaryKeyRelatedField(
        queryset=Machine.objects.all(),
        error_messages={
            "required": "Please select a machine.",
            "null": "Please select a machine.",
            "does_not_exist": "That machine does not exist.",
        },
    )
    question = serializers.CharField(
        max_length=1000,
        trim_whitespace=True,
        error_messages={
            "required": "Please type a question.",
            "blank": "Please type a question.",
            "max_length": "The question is too long (maximum 1000 characters).",
        },
    )


class QuestionSourceSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = QuestionSource
        fields = [
            "passage_number",
            "manual_id",
            "manual_name",
            "revision",
            "page_number",
            "text",
            "score",
            "pdf_url",
        ]

    def get_pdf_url(self, obj):
        # The manual may have been deleted since the question was asked.
        if not obj.manual_id:
            return None
        return f"/api/manuals/{obj.manual_id}/pdf/#page={obj.page_number}"


class QuestionDetailSerializer(serializers.ModelSerializer):
    """A question with its answer and sources. Also usable by the history API."""

    machine_id = serializers.IntegerField(read_only=True)
    machine_name = serializers.CharField(source="machine.name", read_only=True)
    machine_model = serializers.CharField(source="machine.model", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    sources = QuestionSourceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "username",
            "machine_id",
            "machine_name",
            "machine_model",
            "text",
            "answer",
            "answered",
            "created_at",
            "sources",
        ]

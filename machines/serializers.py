from rest_framework import serializers

from .models import Machine, Manual
from .services import extract_pdf_text


MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


class ManualUploadSerializer(serializers.Serializer):
    machine_name = serializers.CharField(
        max_length=255,
        trim_whitespace=True
    )
    machine_model = serializers.CharField(
        max_length=255,
        trim_whitespace=True
    )
    name = serializers.CharField(
        max_length=255,
        trim_whitespace=True
    )
    revision = serializers.CharField(
        max_length=100,
        trim_whitespace=True
    )
    file = serializers.FileField()

    def validate_file(self, value):
        # 1. Reject empty files
        if value.size == 0:
            raise serializers.ValidationError(
                "The uploaded file is empty."
            )

        # 2. Maximum file size: 25 MB
        if value.size > MAX_FILE_SIZE_BYTES:
            raise serializers.ValidationError(
                "File size exceeds the 25 MB limit."
            )

        # 3. Check PDF extension (case-insensitive)
        filename = getattr(value, "name", "") or ""

        if not filename.lower().endswith(".pdf"):
            raise serializers.ValidationError(
                "The uploaded file must have a .pdf extension."
            )

        # 4. Check PDF magic bytes
        initial_pos = value.tell() if hasattr(value, "tell") else 0
        header = value.read(5)

        if hasattr(value, "seek"):
            value.seek(initial_pos)

        if not header.startswith(b"%PDF-"):
            raise serializers.ValidationError(
                "Invalid file content: The file is not a valid PDF document."
            )

        return value

    def validate(self, data):
        # Normalize whitespace
        machine_name = data.get("machine_name", "").strip()
        machine_model = data.get("machine_model", "").strip()
        manual_name = data.get("name", "").strip()
        revision = data.get("revision", "").strip()

        # Check for duplicate manual revision
        if Manual.objects.filter(
            machine__name=machine_name,
            machine__model=machine_model,
            name=manual_name,
            revision=revision,
        ).exists():
            raise serializers.ValidationError(
                "A manual with this revision already exists for this machine."
            )

        return data

    def create(self, validated_data):
        machine_name = validated_data["machine_name"].strip()
        machine_model = validated_data["machine_model"].strip()
        manual_name = validated_data["name"].strip()
        revision = validated_data["revision"].strip()
        uploaded_file = validated_data["file"]

        request = self.context.get("request")

        uploaded_by = (
            request.user
            if request and request.user.is_authenticated
            else None
        )

        # Create machine if it does not already exist
        machine, _ = Machine.objects.get_or_create(
            name=machine_name,
            model=machine_model,
        )

        # Create manual
        manual = Manual.objects.create(
            machine=machine,
            name=manual_name,
            revision=revision,
            file=uploaded_file,
            uploaded_by=uploaded_by,
        )

        # Extract text from the uploaded PDF
        try:
            extract_pdf_text(manual)

        except ValueError as error:
            manual.file.delete(save=False)
            manual.delete()

            raise serializers.ValidationError({
                "file": str(error)
            })

        return manual
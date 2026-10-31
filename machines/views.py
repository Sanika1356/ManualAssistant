
from django.http import FileResponse
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import (
    IsAdministrator,
    IsEngineer,
    IsSupervisor,
)

from .models import Manual
from .serializers import ManualUploadSerializer


class ManualUploadAPIView(APIView):
    """
    API endpoint for Administrators to upload PDF manuals for machines.
    """

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, IsAdministrator]

    def post(self, request, *args, **kwargs):
        serializer = ManualUploadSerializer(
            data=request.data,
            context={"request": request},
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        manual = serializer.save()

        response_data = {
            "id": manual.id,
            "name": manual.name,
            "revision": manual.revision,
            "machine_id": manual.machine.id,
            "machine_name": manual.machine.name,
            "machine_model": manual.machine.model,
            "uploaded_at": manual.uploaded_at.isoformat(),
        }

        return Response(
            response_data,
            status=status.HTTP_201_CREATED,
        )


class ManualPDFViewAPIView(APIView):
    """
    Protected endpoint for viewing uploaded PDF manuals.

    Only Administrators, Engineers and Supervisors can view manuals.
    """

    permission_classes = [
        IsAuthenticated,
        (IsAdministrator | IsEngineer | IsSupervisor),
    ]

    def get(self, request, manual_id, *args, **kwargs):

        manual = get_object_or_404(Manual, id=manual_id)

        if not manual.file:
            return Response(
                {"detail": "PDF file not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            pdf_file = manual.file.open("rb")

        except (FileNotFoundError, OSError, ValueError):
            return Response(
                {"detail": "The requested PDF file is unavailable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        response = FileResponse(
            pdf_file,
            content_type="application/pdf",
            as_attachment=False,
            filename=f"{manual.name}.pdf",
        )

        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"

        return response

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdministrator
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
        return Response(response_data, status=status.HTTP_201_CREATED)

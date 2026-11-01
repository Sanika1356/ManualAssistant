import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsEngineer

from .llm import LLMUnavailable
from .serializers import AskRequestSerializer, QuestionDetailSerializer
from .services import answer_question

logger = logging.getLogger(__name__)


class AskAPIView(APIView):
    """
    POST /api/ask/

    Engineers send {"machine": <id>, "question": "<text>"} and receive the
    saved question with its answer and source passages.
    """

    permission_classes = [IsAuthenticated, IsEngineer]

    def post(self, request, *args, **kwargs):
        serializer = AskRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            question = answer_question(
                user=request.user,
                machine=serializer.validated_data["machine"],
                question_text=serializer.validated_data["question"],
            )
        except LLMUnavailable as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            logger.exception("Answering a question failed")
            return Response(
                {"detail": "The assistant could not answer right now. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            QuestionDetailSerializer(question).data,
            status=status.HTTP_201_CREATED,
        )

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsEngineer, IsSupervisor

from .llm import LLMUnavailable
from .serializers import AskRequestSerializer, QuestionDetailSerializer
from .services import answer_question
from .models import Question

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
class QuestionHistoryAPIView(APIView):
    """
    GET /api/history/

    Engineers can view their own question history.
    Supervisors can view all engineers' question history.
    """

    permission_classes = [
        IsAuthenticated,
        IsEngineer | IsSupervisor,
    ]

    def get(self, request, *args, **kwargs):

        questions = Question.objects.select_related(
            "user", "machine"
        ).prefetch_related(
            "sources"
        )

        if request.user.groups.filter(name="Engineer").exists():
            questions = questions.filter(user=request.user)

        serializer = QuestionDetailSerializer(
            questions,
            many=True
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
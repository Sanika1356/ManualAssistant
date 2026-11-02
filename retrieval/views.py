import logging
from accounts.permissions import IsEngineer, IsSupervisor
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Question
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

class HistoryAPIView(APIView):
    """
    GET /api/history/

    Engineers see their own question history.
    Supervisors see all engineers' question history.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        is_engineer = IsEngineer().has_permission(request, self)
        is_supervisor = IsSupervisor().has_permission(request, self)

        if not (is_engineer or is_supervisor):
            return Response(
                {"detail": "Only Engineers and Supervisors can view history."},
                status=status.HTTP_403_FORBIDDEN,
            )

        questions = Question.objects.select_related(
            "user", "machine"
        ).prefetch_related("sources")

        if is_engineer:
            questions = questions.filter(user=request.user)

        question_status = request.query_params.get("status")

        if question_status == "insufficient_evidence":
            questions = questions.filter(status=Question.Status.INSUFFICIENT_EVIDENCE)
        elif question_status == "answered":
            questions = questions.filter(status=Question.Status.ANSWERED)
        elif question_status:
            return Response(
                {"detail": "Invalid status. Use 'answered' or 'insufficient_evidence'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = QuestionDetailSerializer(questions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
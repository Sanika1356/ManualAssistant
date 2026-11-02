from django.urls import path
from .views import AskAPIView, QuestionHistoryAPIView

urlpatterns = [
    path("ask/", AskAPIView.as_view(), name="ask"),
    path("history/", QuestionHistoryAPIView.as_view(), name="question-history"),
]


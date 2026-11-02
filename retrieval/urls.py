from django.urls import path
 p4-ask-history
from .views import AskAPIView, QuestionHistoryAPIView

urlpatterns = [
    path("ask/", AskAPIView.as_view(), name="ask"),
    path("history/", QuestionHistoryAPIView.as_view(), name="question-history"),
]



from .views import AskAPIView, HistoryAPIView

urlpatterns = [
    path("ask/", AskAPIView.as_view(), name="ask"),
    path("history/", HistoryAPIView.as_view(), name="history"),
]
 main

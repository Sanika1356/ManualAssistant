from django.urls import path

from .views import AskAPIView, HistoryAPIView

urlpatterns = [
    path("ask/", AskAPIView.as_view(), name="ask"),
    path("history/", HistoryAPIView.as_view(), name="history"),
]
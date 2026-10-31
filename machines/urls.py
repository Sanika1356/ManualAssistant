from django.urls import path
from .views import ManualUploadAPIView

urlpatterns = [
    path("manuals/upload/", ManualUploadAPIView.as_view(), name="manual-upload"),
]


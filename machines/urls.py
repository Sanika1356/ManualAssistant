
from django.urls import path

from .views import ManualPDFViewAPIView, ManualUploadAPIView


urlpatterns = [
    path(
        "manuals/upload/",
        ManualUploadAPIView.as_view(),
        name="manual-upload",
    ),
    path(
        "manuals/<int:manual_id>/pdf/",
        ManualPDFViewAPIView.as_view(),
        name="manual-pdf-view",
    ),
]


from django.urls import path

from .views import (
    MachineListCreateAPIView,
    ManualListAPIView,
    ManualPDFViewAPIView,
    ManualUploadAPIView,
)


urlpatterns = [
    path(
        "machines/",
        MachineListCreateAPIView.as_view(),
        name="machine-list-create",
    ),
    path(
        "manuals/",
        ManualListAPIView.as_view(),
        name="manual-list",
    ),
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

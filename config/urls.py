from django.contrib import admin
from django.urls import path, include

from accounts.views import login_page, dashboard_page

urlpatterns = [
    path("admin/", admin.site.urls),

    # Website pages
    path("login/", login_page, name="login-page"),
    path("dashboard/", dashboard_page, name="dashboard"),

    # API endpoints
    path("api/", include("accounts.urls")),
    path("api/", include("machines.urls")),
    path("api/", include("retrieval.urls")),
]
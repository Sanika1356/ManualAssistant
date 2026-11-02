from django.urls import path

from .views import (
    csrf_token,
    LoginAPI,
    SignupAPI,
    MeAPI,
    LogoutAPI,
)

urlpatterns = [
    path("csrf/", csrf_token, name="csrf-token"),
    path("login/", LoginAPI.as_view(), name="login"),
    path("signup/", SignupAPI.as_view(), name="signup"),
    path("me/", MeAPI.as_view(), name="me"),
    path("logout/", LogoutAPI.as_view(), name="logout"),
]
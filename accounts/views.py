from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .serializers import LoginSerializer


@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({"message": "CSRF cookie set"})


@method_decorator(csrf_protect, name="dispatch")
class LoginAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(
            request=request._request,
            username=username,
            password=password
        )

        if user is None:
            return Response(
                {"error": "Invalid username or password"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        login(request._request, user)

        groups = list(
            user.groups.values_list("name", flat=True)
        )

        roles = [
            role for role in
            ["Administrator", "Engineer", "Supervisor"]
            if role in groups
        ]

        if len(roles) != 1:
            logout(request._request)
            return Response(
                {"error": "Your account must have exactly one valid role."},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response({
            "message": "Login successful",
            "username": user.username,
            "role": roles[0]
        })


class MeAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        groups = list(
            request.user.groups.values_list("name", flat=True)
        )

        roles = [
            role for role in
            ["Administrator", "Engineer", "Supervisor"]
            if role in groups
        ]

        if len(roles) != 1:
            return Response(
                {"error": "Your account must have exactly one valid role."},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response({
            "username": request.user.username,
            "role": roles[0]
        })


class LogoutAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request._request)

        return Response({
            "message": "Logged out successfully"
        })
def login_page(request):
    if request.user.is_authenticated:

        groups = list(
            request.user.groups.values_list("name", flat=True)
        )

        roles = [
            role for role in ["Administrator", "Engineer", "Supervisor"]
            if role in groups
        ]

        # Only redirect users who have a valid application role
        if len(roles) == 1:
            return redirect("dashboard")

    return render(request, "accounts/login.html")


def dashboard_page(request):
    if not request.user.is_authenticated:
        return redirect("login-page")

    groups = list(request.user.groups.values_list("name", flat=True))

    roles = [
        role for role in ["Administrator", "Engineer", "Supervisor"]
        if role in groups
    ]

    if len(roles) != 1:
        return redirect("login-page")

    return render(
        request,
        "accounts/dashboard.html",
        {
            "username": request.user.username,
            "role": roles[0],
        }
    )
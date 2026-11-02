from django.test import TestCase
from django.contrib.auth.models import User, Group, AnonymousUser
from rest_framework.test import APIClient, APIRequestFactory

from .permissions import (
    IsAdministrator,
    IsEngineer,
    IsSupervisor,
)


class RolePermissionTests(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

        self.roles = [
            "Administrator",
            "Engineer",
            "Supervisor",
        ]

        self.users = {}

        for role in self.roles:
            group, created = Group.objects.get_or_create(name=role)

            user = User.objects.create_user(
                username=f"{role.lower()}_test",
                password="TestPassword@123"
            )

            user.groups.add(group)
            self.users[role] = user

        self.permissions = {
            "Administrator": IsAdministrator(),
            "Engineer": IsEngineer(),
            "Supervisor": IsSupervisor(),
        }

    def make_request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_only_matching_role_is_allowed(self):
        for required_role, permission in self.permissions.items():

            for actual_role, user in self.users.items():
                with self.subTest(
                    required=required_role,
                    actual=actual_role
                ):
                    request = self.make_request(user)

                    self.assertEqual(
                        permission.has_permission(request, None),
                        required_role == actual_role
                    )

    def test_anonymous_users_are_denied(self):
        for permission in self.permissions.values():
            request = self.make_request(AnonymousUser())

            self.assertFalse(
                permission.has_permission(request, None)
            )

    def test_users_without_roles_are_denied(self):
        user = User.objects.create_user(
            username="no_role_test",
            password="TestPassword@123"
        )

        for permission in self.permissions.values():
            request = self.make_request(user)

            self.assertFalse(
                permission.has_permission(request, None)
            )


class SignupTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def signup(self, **extra):
        data = {"username": "new_engineer", "password": "Str0ng-Pass-77"}
        data.update(extra)
        return self.client.post("/api/signup/", data, format="json")

    def test_new_account_is_always_an_engineer(self):
        response = self.signup(role="Administrator", is_superuser=True, is_staff=True)

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="new_engineer")
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["Engineer"])
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)

    def test_new_user_can_log_in(self):
        self.signup()
        response = self.client.post(
            "/api/login/",
            {"username": "new_engineer", "password": "Str0ng-Pass-77"},
            format="json",
        )
        self.assertEqual(response.data["role"], "Engineer")

    def test_duplicate_username_is_refused(self):
        self.signup()
        response = self.signup(username="NEW_engineer")
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)

    def test_weak_password_is_refused(self):
        response = self.signup(password="12345")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)
        self.assertFalse(User.objects.filter(username="new_engineer").exists())

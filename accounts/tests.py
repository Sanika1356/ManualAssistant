from django.test import TestCase
from django.contrib.auth.models import User, Group, AnonymousUser
from rest_framework.test import APIRequestFactory

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

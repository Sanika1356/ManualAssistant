
from rest_framework.permissions import BasePermission


class IsAdministrator(BasePermission):
    """
    Allows access only to Administrator users.
    """

    message = "Only Administrators can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(
                name="Administrator"
            ).exists()
        )


class IsEngineer(BasePermission):
    """
    Allows access only to Engineer users.
    """

    message = "Only Engineers can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(
                name="Engineer"
            ).exists()
        )


class IsSupervisor(BasePermission):
    """
    Allows access only to Supervisor users.
    """

    message = "Only Supervisors can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(
                name="Supervisor"
            ).exists()
        )

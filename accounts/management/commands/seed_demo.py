from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    help = "Create demo users for all three roles"

    def handle(self, *args, **kwargs):

        demo_users = [
            {
                "username": "admin_demo",
                "password": "AdminDemo@123",
                "role": "Administrator",
            },
            {
                "username": "engineer_demo",
                "password": "EngineerDemo@123",
                "role": "Engineer",
            },
            {
                "username": "supervisor_demo",
                "password": "SupervisorDemo@123",
                "role": "Supervisor",
            },
        ]

        for item in demo_users:
            group = Group.objects.get(name=item["role"])

            user, created = User.objects.get_or_create(
                username=item["username"]
            )

            user.set_password(item["password"])
            user.is_active = True
            user.save()

            # Remove any previous role assignments
            user.groups.clear()

            # Assign the correct role
            user.groups.add(group)

            action = "Created" if created else "Updated"

            self.stdout.write(
                self.style.SUCCESS(
                    f'{action} {item["username"]} '
                    f'as {item["role"]}'
                )
            )

        self.stdout.write(
            self.style.SUCCESS("All demo accounts are ready!")
        )

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a default user for development'

    def handle(self, *args, **kwargs):
        username = 'GuestUser'
        email = 'default@example.com'
        password = 'admin'

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User "{username}" already exists'))
        else:
            User.objects.create_user(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Successfully created user "{username}"'))

        # Print the user's ID
        user = User.objects.get(username=username)
        self.stdout.write(self.style.SUCCESS(f'User ID: {user.id}'))
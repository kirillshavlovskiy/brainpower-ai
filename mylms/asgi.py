import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mylms.settings')

# Initialize Django
django.setup()

# Now import your custom middleware and routing
from courses.middleware import UserIDAuthMiddleware
from courses import routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
            URLRouter(
                routing.websocket_urlpatterns
            )
    ),
})
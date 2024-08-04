import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import courses.routing  # replace 'your_app' with your actual app name

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mylms.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            courses.routing.websocket_urlpatterns
        )
    ),
})
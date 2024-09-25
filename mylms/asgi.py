import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from sandbox import routing as sandbox_routing
from courses import routing as courses_routing
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            sandbox_routing.websocket_urlpatterns +
            courses_routing.websocket_urlpatterns
        )
    ),
})
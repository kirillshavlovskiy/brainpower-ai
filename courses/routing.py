from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path, path

from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/livechat_autogen/$', consumers.AsyncChatConsumer.as_asgi()),
    re_path(r'ws/file_structure/$', consumers.FileStructureConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    'websocket': URLRouter(
        websocket_urlpatterns
    )
})
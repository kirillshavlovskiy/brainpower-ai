from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/courses/livechat_autogen/$', consumers.AsyncChatConsumer.as_asgi()),
    re_path(r'ws/courses/file_structure/$', consumers.FileStructureConsumer.as_asgi()),
]

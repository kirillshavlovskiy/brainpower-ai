from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/livechat_autogen/$', consumers.AsyncChatConsumer.as_asgi()),
    re_path(r'ws/file_structure/$', consumers.FileStructureConsumer.as_asgi()),
    re_path(r'^ws/deployment/(?P<task_id>[\w.-]+)/$', consumers.DeploymentConsumer.as_asgi()),
]

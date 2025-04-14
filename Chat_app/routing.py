from django.urls import re_path
from .consumers import *

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<conversation_pk>[0-9a-f-]+)/$", ChatConsumer.as_asgi()),  # ✅ استفاده از UUID در WebSocket

    re_path(r"ws/channel/(?P<channel_username>[\w-]+)/$", ChannelConsumer.as_asgi()),  # ✅ مسیر درست برای چنل

]

from django.urls import re_path
from .consumers import ChatConsumer, ChannelConsumer

# WebSocket routing for private and channel chats
websocket_urlpatterns = [
    # Route for 1-on-1 private chat WebSocket
    re_path(r"ws/chat/(?P<conversation_pk>[0-9a-f-]+)/$", ChatConsumer.as_asgi()),

    # Route for channel (group) chat WebSocket
    re_path(r"ws/channel/(?P<channel_username>[\w-]+)/$", ChannelConsumer.as_asgi()),
]

import os
import django

# Set default settings for the Django project
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chat_project.settings")
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from Chat_app.routing import websocket_urlpatterns

# ASGI application configuration to handle both HTTP and WebSocket protocols
application = ProtocolTypeRouter({
    # Django's default HTTP handling
    "http": get_asgi_application(),

    # WebSocket handling with authentication support
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})

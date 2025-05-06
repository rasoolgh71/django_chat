from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    ConversationView,
    CreateConversationAjaxView,
    ChannelCreateView,
    ChannelDetailView,
    ManageChannelView,index
)

app_name = "chat"

urlpatterns = [
    # Route for viewing a conversation by its primary key
    path("", index, name="index"),
    path("chat/<int:pk>/", ConversationView.as_view(), name="conversation"),

    # AJAX route to create a new conversation (likely from frontend interaction)
    path("chat/createconversation/", CreateConversationAjaxView.as_view(), name="create_conversation_ajax"),

    # Route to create a new chat channel
    path("chat/channelcreate/", ChannelCreateView.as_view(), name="channel_create"),

    # Route to view a specific channel by its primary key
    path("chat/channel/<int:pk>/", ChannelDetailView.as_view(), name="channel_detail"),

    # Route for managing chat channels (possibly user-created channels)
    path("channel/manage/", ManageChannelView.as_view(), name="manage_channel"),
]

# Serving media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

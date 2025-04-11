from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static

app_name = "chat"
urlpatterns = [
    path("chat/<int:pk>/", ConversationView.as_view(), name="conversation"),

    path("chat/list/", ConversationListView.as_view(), name="conversation_list"),
    path("chat/createconversation/", CreateConversationAjaxView.as_view(), name="create_conversation_ajax"),

    path("chat/channelcreate/", ChannelCreateView.as_view(), name="channel_create"),
    path("chat/channel/<int:pk>/", ChannelDetailView.as_view(), name="channel_detail"),
    path("channel/manage/", ManageChannelView.as_view(), name="manage_channel"),

]
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
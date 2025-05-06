from django.views import View
from django.views.generic import DetailView, CreateView
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .models import Conversation, Message, Channel, ChannelMember, ChannelMessage
from .forms import ChannelCreateForm
from django.shortcuts import render, redirect

import base64, os, time


# -------------------------
# Detail view for 1-on-1 conversations
# -------------------------


def index(request):
    return render(request, 'chat_app/chat.html', {'title': 'صفحه اصلی'})

class ConversationView(DetailView):
    model = Conversation
    template_name = "Chat_app/conversation.html"
    context_object_name = "conversation"

    def dispatch(self, request, *args, **kwargs):
        # Temporary login bypass for testing (use actual authentication in production)
        if not request.user.is_authenticated:
            request.user = get_user_model().objects.get(pk=1)
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        return get_object_or_404(Conversation, pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        conversation = self.object

        # Determine the user's conversations and the chat partner
        if user == conversation.user1:
            conversations = Conversation.objects.filter(user1=user)
            chat_partner = conversation.user2
        elif user == conversation.user2:
            conversations = Conversation.objects.filter(user2=user)
            chat_partner = conversation.user1
        else:
            conversations = Conversation.objects.none()
            chat_partner = None

        # Add context data for rendering the chat UI
        context.update({
            "messages": Message.objects.all(),
            "joined_channels": Channel.objects.filter(members__user=user),
            "unjoined_channels": Channel.objects.exclude(members__user=user),
            "channelList": Channel.objects.all(),
            "conversations": conversations,
            "chat_partner": chat_partner,
        })
        return context


# -------------------------
# AJAX view to create a new conversation
# -------------------------
class CreateConversationAjaxView(View):
    def post(self, request):
        user = get_user_model().objects.get(pk=1)
        target_user_id = request.POST.get("user_id")

        if not target_user_id:
            return JsonResponse({"error": "Target user ID is required."}, status=400)
        if str(user.id) == target_user_id:
            return JsonResponse({"error": "You can't chat with yourself."}, status=400)

        try:
            other_user = get_user_model().objects.get(pk=target_user_id)
        except get_user_model().DoesNotExist:
            return JsonResponse({"error": "Target user not found."}, status=404)

        # Always create with smaller ID as user1
        user1, user2 = sorted([user, other_user], key=lambda u: u.id)
        conversation, _ = Conversation.objects.get_or_create(user1=user1, user2=user2)

        return JsonResponse({
            "chat_url": reverse("conversation_detail", args=[conversation.pk])
        }, status=201)


# -------------------------
# View for displaying channel details
# -------------------------
class ChannelDetailView(DetailView):
    model = Channel
    template_name = "Chat_app/channel_detail.html"
    context_object_name = "channel"

    def get_queryset(self):
        return Channel.objects.prefetch_related("members")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_user_model().objects.get(pk=1)
        channel = self.object

        context.update({
            "messages": channel.messages.select_related("sender").order_by("created_at"),
            "is_member": channel.members.filter(user=user).exists(),
            "joined_channels": Channel.objects.filter(members__user=user),
            "unjoined_channels": Channel.objects.exclude(members__user=user),
            "channelList": Channel.objects.all(),
            "conversations": Conversation.objects.filter(user1=user) | Conversation.objects.filter(user2=user),
            "user_test": user,
        })
        return context


# -------------------------
# View to create a new channel
# -------------------------
class ChannelCreateView(CreateView):
    model = Channel
    form_class = ChannelCreateForm
    template_name = "Chat_app/channel_create.html"

    def form_valid(self, form):
        user = get_user_model().objects.get(pk=1)
        form.instance.owner = user
        self.object = form.save()

        # Automatically make creator the admin of the channel
        ChannelMember.objects.create(channel=self.object, user=user, role="admin")
        return redirect("chat:channel_detail", pk=self.object.pk)


# -------------------------
# Basic channel management: join, leave, delete
# -------------------------
class ManageChannelView(View):
    def post(self, request):
        action = request.POST.get("action")
        username = request.POST.get("username")
        message_id = request.POST.get("message_id")

        user = get_user_model().objects.get(pk=1)
        channel = get_object_or_404(Channel, username=username)

        if action == "delete_channel" and user == channel.owner:
            channel.delete()
            return redirect("conversation_list")

        if action == "leave_channel":
            ChannelMember.objects.filter(channel=channel, user=user).delete()
            return redirect("conversation_list")

        if action == "join_channel":
            if not ChannelMember.objects.filter(channel=channel, user=user).exists():
                ChannelMember.objects.create(channel=channel, user=user)
            return redirect("channel_detail", pk=channel.pk)

        if action == "delete_message":
            message = get_object_or_404(ChannelMessage, id=message_id, channel=channel)
            if user == channel.owner:
                message.delete()
            return redirect("channel_detail", pk=channel.pk)

        return redirect("chat:conversation_list")


# -------------------------
# File upload handler for base64-encoded files
# -------------------------
@csrf_exempt
def upload_file(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

    file_data = request.POST.get("file_data")
    file_type = request.POST.get("file_type")

    if not file_data or not file_type:
        return JsonResponse({"error": "File data or type missing."}, status=400)

    try:
        format, imgstr = file_data.split(";base64,")
        ext = format.split("/")[-1].lower()
        allowed = ["jpg", "jpeg", "png", "pdf", "mp4", "mp3"]
        blocked = ["exe", "php", "sh", "bat", "py"]

        if ext in blocked:
            return JsonResponse({"error": "File type is not allowed."}, status=400)
        if ext not in allowed:
            return JsonResponse({"error": "Unsupported file type."}, status=400)

        decoded_file = base64.b64decode(imgstr)
        if len(decoded_file) > 5 * 1024 * 1024:
            return JsonResponse({"error": "File size exceeds the limit."}, status=400)

        folder_path = os.path.join(settings.MEDIA_ROOT, "channel_files")
        os.makedirs(folder_path, exist_ok=True)

        filename = f"user_{int(time.time())}.{ext}"
        filepath = os.path.join(folder_path, filename)

        with open(filepath, "wb") as f:
            f.write(decoded_file)

        file_url = f"/media/channel_files/{filename}"
        return JsonResponse({"file_url": file_url}, status=201)

    except Exception as e:
        return JsonResponse({"error": f"File processing failed: {e}"}, status=500)

from django.views import View
from django.views.generic import ListView, DetailView, CreateView
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import *
from .forms import *
import base64, os, time

# -------------------------
# Conversation Detail View
# -------------------------
class ConversationView(DetailView):
    model = Conversation
    template_name = "Chat_app/conversation.html"
    context_object_name = "conversation"

    def dispatch(self, request, *args, **kwargs):
        # Automatically use a sample user if not authenticated
        if not request.user.is_authenticated:
            request.user = get_user_model().objects.get(pk=1)
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return get_object_or_404(Conversation, pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super().get_context_data(**kwargs)
        conversation = self.object

        # Determine partner and user's conversation list
        if user == conversation.user1:
            conversations = Conversation.objects.filter(user1=user)
            chat_partner = conversation.user2
        elif user == conversation.user2:
            conversations = Conversation.objects.filter(user2=user)
            chat_partner = conversation.user1
        else:
            conversations = Conversation.objects.none()
            chat_partner = None

        context.update({
            "joined_channels": Channel.objects.filter(members__user=user),
            "unjoined_channels": Channel.objects.exclude(members__user=user),
            "channelList": Channel.objects.all(),
            "conversations": conversations,
            "chat_partner": chat_partner,
        })
        return context


# -------------------------
# Conversation List View
# -------------------------
class ConversationListView(ListView):
    model = Conversation
    template_name = "Chat_app/conversation_list.html"
    context_object_name = "conversations"

    def dispatch(self, request, *args, **kwargs):
        # Use a default user for test mode
        if not request.user.is_authenticated:
            request.user = get_user_model().objects.get(pk=1)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(user1=user) | Conversation.objects.filter(user2=user)

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super().get_context_data(**kwargs)
        conversations = context["conversations"]

        # Count unread messages per conversation
        unread_messages = {
            conv.id: conv.messages.filter(read=False).exclude(sender=user).count()
            for conv in conversations
        }

        context.update({
            "unread_messages": unread_messages,
            "joined_channels": Channel.objects.filter(members__user=user),
            "unjoined_channels": Channel.objects.exclude(members__user=user),
            "channelList": Channel.objects.all(),
        })
        return context


# -------------------------
# Create Conversation via AJAX (no login required)
# -------------------------
class CreateConversationAjaxView(View):
    def post(self, request, *args, **kwargs):
        user = get_user_model().objects.get(pk=1)  # Sample user

        target_user_id = request.POST.get("user_id")
        if not target_user_id:
            return JsonResponse({"error": "Target user ID is required."}, status=400)

        if str(user.id) == target_user_id:
            return JsonResponse({"error": "You can't chat with yourself."}, status=400)

        try:
            other_user = get_user_model().objects.get(pk=target_user_id)
        except get_user_model().DoesNotExist:
            return JsonResponse({"error": "Target user not found."}, status=404)

        user1, user2 = sorted([user, other_user], key=lambda u: u.id)
        conversation, created = Conversation.objects.get_or_create(user1=user1, user2=user2)

        return JsonResponse({
            "chat_url": reverse("conversation_detail", args=[conversation.pk])
        }, status=201)


# -------------------------
# Channel Detail View
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

        context["messages"] = channel.messages.select_related("sender").order_by("created_at")
        context["is_member"] = channel.members.filter(user=user).exists()
        context["joined_channels"] = Channel.objects.filter(members__user=user)
        context["unjoined_channels"] = Channel.objects.exclude(members__user=user)
        context["channelList"] = Channel.objects.all()
        context["conversations"] = Conversation.objects.filter(user1=user) | Conversation.objects.filter(user2=user)

        return context


# -------------------------
# Create Channel
# -------------------------
class ChannelCreateView(CreateView):
    model = Channel
    form_class = ChannelCreateForm
    template_name = "Chat_app/channel_create.html"

    def form_valid(self, form):
        test_user = get_user_model().objects.get(pk=1)
        form.instance.owner = test_user
        self.object = form.save()

        # Assign user as admin in the channel
        ChannelMember.objects.create(
            channel=self.object,
            user=test_user,
            role="admin"
        )
        return redirect("chat:channel_detail", pk=self.object.pk)


# -------------------------
# Manage Channel Actions (test mode)
# -------------------------
class ManageChannelView(View):
    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        username = request.POST.get("username")
        message_id = request.POST.get("message_id")

        test_user = get_user_model().objects.get(pk=1)
        channel = get_object_or_404(Channel, username=username)

        if action == "delete_channel" and test_user == channel.owner:
            channel.delete()
            return redirect("conversation_list")

        elif action == "leave_channel":
            member = ChannelMember.objects.filter(channel=channel, user=test_user).first()
            if member:
                member.delete()
                return redirect("conversation_list")

        elif action == "join_channel":
            if not ChannelMember.objects.filter(channel=channel, user=test_user).exists():
                ChannelMember.objects.create(channel=channel, user=test_user)
                return redirect("channel_detail", pk=channel.id)

        elif action == "delete_message":
            message = get_object_or_404(ChannelMessage, id=message_id, channel=channel)
            if test_user == channel.owner:
                message.delete()
                return redirect("channel_detail", pk=channel.id)

        return redirect("chat:conversation_list")


# -------------------------
# File Upload Handler
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

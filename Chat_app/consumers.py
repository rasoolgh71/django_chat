# chat/consumers.py

import os
import json
import uuid
import base64
import time
import jwt

from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from jwt.exceptions import InvalidTokenError
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import get_object_or_404
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Conversation, Message, Channel, ChannelMessage, ChannelMember

User = get_user_model()
online_users = {}

# -------------------------------
# online states
# -------------------------------
def set_user_online(user_email):
    online_users[user_email] = True

def set_user_offline(user_email):
    online_users[user_email] = False

def is_user_online(user_email):
    return online_users.get(user_email, False)


# -------------------------------
# WebSocket for private chat
# -------------------------------
class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_uuid = self.scope["url_route"]["kwargs"]["conversation_pk"]
        self.room_group_name = f"chat_{self.conversation_uuid}"
        self.user = self.scope["user"]

        if not self.user or isinstance(self.user, AnonymousUser):
            # ست کردن کاربر تستی
            self.user = await sync_to_async(User.objects.get)(pk=1)

        self.conversation = await sync_to_async(get_object_or_404)(Conversation, pk=self.conversation_uuid)
        self.opponent_user = await self.get_opponent_user()

        set_user_online(self.user.email)
        await self.accept()
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        if self.opponent_user:
            await self.send(json.dumps({
                "type": "opponent_email", "email": self.opponent_user.email
            }))
            await self.send(json.dumps({
                "type": "online_status", "user": self.opponent_user.email,
                "online": is_user_online(self.opponent_user.email)
            }))

        await self.channel_layer.group_send(self.room_group_name, {
            "type": "online_status", "user": self.user.email, "online": True
        })

    async def disconnect(self, close_code):
        """مدیریت خروج کاربر از چت"""
        if self.user and not isinstance(self.user, AnonymousUser):
            set_user_offline(self.user.email)
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "online_status", "user": self.user.email, "online": False}
            )
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get("type")

        if event_type == "typing":
            await self.channel_layer.group_send(self.room_group_name, {
                "type": "typing_status", "user": self.user.email, "typing": data["typing"]
            })

        elif event_type == "message":
            message_text = data.get("message", "")
            message_type = data.get("message_type", "text")
            file_data = data.get("file_url")

            file_url = await self.save_file(file_data, message_type) if file_data else None
            message = await self.save_message(self.user, message_text, message_type, file_url)

            await self.channel_layer.group_send(self.room_group_name, {
                "type": "chat_message",
                "message": message.text,
                "sender": self.user.email,
                "message_type": message.message_type,
                "file_url": file_url
            })

    async def chat_message(self, event):
        await self.send(json.dumps(event))

    async def typing_status(self, event):
        await self.send(json.dumps(event))

    async def online_status(self, event):
        await self.send(json.dumps(event))

    @database_sync_to_async
    def get_opponent_user(self):
        if self.user == self.conversation.user1:
            return self.conversation.user2
        elif self.user == self.conversation.user2:
            return self.conversation.user1
        return None

    @database_sync_to_async
    def save_message(self, sender, text, message_type, file_url=None):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=sender,
            text=text,
            message_type=message_type
        )
        if file_url:
            message.file.name = file_url.replace("/media/", "")
            message.save()
        return message

    @database_sync_to_async
    def save_file(self, file_data, message_type):
        try:
            format, file_str = file_data.split(";base64,")
            ext = format.split("/")[-1]
            allowed = ["jpg", "jpeg", "png", "pdf", "mp3", "mp4"]
            blocked = ["exe", "php", "sh", "bat", "py"]

            if ext in blocked or ext not in allowed:
                return None

            decoded_file = base64.b64decode(file_str)
            if len(decoded_file) > 5 * 1024 * 1024:
                return None

            folder = os.path.join("chat_files", str(self.conversation.pk))
            filename = f"{uuid.uuid4()}.{ext}"
            path = os.path.join(folder, filename)

            file_content = ContentFile(decoded_file)
            saved_path = default_storage.save(path, file_content)
            return saved_path.replace(settings.MEDIA_ROOT, "").lstrip("/")
        except Exception:
            return None


# -------------------------------
# WebSocket for channels
# -------------------------------
class ChannelConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.channel_username = self.scope['url_route']['kwargs']['channel_username']
        self.room_group_name = f"chat_{self.channel_username}"
        self.user = self.scope["user"]

        if isinstance(self.user, AnonymousUser):
            # استفاده از یوزر تستی اگر احراز هویت نشده بود
            self.user = await sync_to_async(User.objects.get)(pk=1)

        self.channel = await sync_to_async(get_object_or_404)(Channel, username=self.channel_username)

        if not await self.is_channel_member():
            await self.close()
            return

        await self.accept()
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get("type")

        if event_type == "typing":
            await self.channel_layer.group_send(self.room_group_name, {
                "type": "typing_status", "user": self.user.email, "typing": data["typing"]
            })

        elif event_type == "message":
            message_text = data.get("message", "")
            message_type = data.get("message_type", "text")
            file_data = data.get("file_url")

            file_url = await self.save_file(file_data, message_type) if file_data else None
            message = await self.save_message(message_text, message_type, file_url)

            await self.channel_layer.group_send(self.room_group_name, {
                "type": "chat_message",
                "message": message.text,
                "sender": self.user.email,
                "message_type": message.message_type,
                "file_url": message.file.url if message.file else None
            })

    async def chat_message(self, event):
        await self.send(json.dumps(event))

    async def typing_status(self, event):
        await self.send(json.dumps(event))

    @database_sync_to_async
    def is_channel_member(self):
        return ChannelMember.objects.filter(channel=self.channel, user=self.user).exists()

    @database_sync_to_async
    def save_message(self, text, message_type, file_url=None):
        message = ChannelMessage.objects.create(
            channel=self.channel,
            sender=self.user,
            text=text if message_type == "text" else "",
            message_type=message_type
        )
        if file_url:
            message.file.name = file_url.replace("/media/", "")
            message.save()
        return message

    @database_sync_to_async
    def save_file(self, file_data, message_type):
        try:
            format, file_str = file_data.split(";base64,")
            ext = format.split("/")[-1].lower()
            allowed = ["jpg", "jpeg", "png", "pdf", "mp3", "mp4"]
            blocked = ["exe", "php", "sh", "bat", "py"]

            if ext in blocked or ext not in allowed:
                return None

            decoded_file = base64.b64decode(file_str)
            if len(decoded_file) > 5 * 1024 * 1024:
                return None

            folder = os.path.join("channel_files", str(self.channel.pk))
            filename = f"{uuid.uuid4()}.{ext}"
            path = os.path.join(folder, filename)

            file_content = ContentFile(decoded_file)
            saved_path = default_storage.save(path, file_content)
            return saved_path.replace(settings.MEDIA_ROOT, "").lstrip("/")
        except Exception:
            return None

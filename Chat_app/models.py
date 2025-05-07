from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.contrib.auth.models import AbstractUser, BaseUserManager
import uuid

# -----------------------------------------
# Custom user model manager
# -----------------------------------------
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.username = email
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

# -----------------------------------------
# Custom user model using email for login
# -----------------------------------------
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


# -----------------------------------------
# One-on-one conversation model
# -----------------------------------------
class Conversation(models.Model):
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations_as_user1')
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations_as_user2')
    created_at = models.DateTimeField(auto_now_add=True)
    user1_typing = models.BooleanField(default=False)
    user2_typing = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user1.email} ↔ {self.user2.email}"


# -----------------------------------------
# Message model for conversations
# -----------------------------------------
class Message(models.Model):
    MESSAGE_TYPES = (
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('file', 'File'),
        ('voice', 'Voice'),
    )
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    file = models.FileField(upload_to="media/", blank=True, null=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender.email}: {self.text[:30]}"


# -----------------------------------------
# Channel (group chat) model
# -----------------------------------------
class Channel(models.Model):
    PERMISSION_CHOICES = (
        ('admins_only', 'Admins only'),
        ('everyone', 'All members'),
    )
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_channels')
    name = models.CharField(max_length=100)
    username = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    post_permission = models.CharField(max_length=15, choices=PERMISSION_CHOICES, default='admins_only')
    image = models.ImageField(upload_to="image_channel/", blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = slugify(self.name) + "-" + str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# -----------------------------------------
# Membership in a channel
# -----------------------------------------
class ChannelMember(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('member', 'Member'),
    )
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='channel_memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} in {self.channel.name} ({self.get_role_display()})"


# -----------------------------------------
# Message sent in a channel
# -----------------------------------------
class ChannelMessage(models.Model):
    MESSAGE_TYPES = (
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('file', 'File'),
        ('voice', 'Voice'),
    )
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='conversation_messages', null=True, blank=True)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="chat_files/", blank=True, null=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.email}: {self.text[:30] if self.text else self.message_type}"

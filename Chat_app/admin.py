from django.contrib import admin
from Chat_app.models import *
# Register your models here.
admin.site.register(Conversation)
admin.site.register(Channel)
admin.site.register(ChannelMessage)
admin.site.register(ChannelMember)
admin.site.register(CustomUser)
admin.site.register(Message)
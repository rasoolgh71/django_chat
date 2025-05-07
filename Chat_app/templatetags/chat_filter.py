from django import template
from Chat_app.models import ChannelMessage  # فرض: مدل پیام شما اینه

register = template.Library()


@register.filter
def message_count(channel):
    return ChannelMessage.objects.filter(channel=channel).count()
from django.db import models
from Chat_app.models import CustomUser
# Create your models here.


class Log(models.Model):

    class Meta:
        verbose_name = 'لاگ'
        verbose_name_plural = 'لاگ ها'
        permissions = (
            ('can_view_log', 'مشاهده لاگ'),

        )

    title = models.CharField(max_length=200)
    user = models.ForeignKey(CustomUser, related_name='log_user', on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.IntegerField()
    status = models.BooleanField(default=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)
    ip = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.title
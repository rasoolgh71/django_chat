from django import forms
from .models import Conversation, Channel, ChannelMessage
from .models import *

# --------------------------
# فرم ساخت مکالمه بین دو کاربر
# --------------------------
class ConversationForm(forms.ModelForm):
    class Meta:
        model = Conversation
        fields = ["user1", "user2"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            # فقط کاربرهای دیگه رو نمایش بده
            self.fields["user1"].queryset = CustomUser.objects.exclude(pk=user.pk)
            self.fields["user2"].queryset = CustomUser.objects.exclude(pk=user.pk)

            self.fields["user1"].initial = user
            self.fields["user1"].widget = forms.HiddenInput()  # کاربر لاگین‌شده رو مخفی نگه داریم

# --------------------------
# فرم ساخت کانال
# --------------------------
class ChannelCreateForm(forms.ModelForm):
    class Meta:
        model = Channel
        fields = ["name", "description", "username"]

    def clean_username(self):
        username = self.cleaned_data["username"]
        if not username:
            raise forms.ValidationError("لطفاً یک نام کاربری وارد کنید.")
        if Channel.objects.filter(username=username).exists():
            raise forms.ValidationError("این نام کاربری قبلاً استفاده شده است.")
        return username

# --------------------------
# فرم ارسال پیام در کانال
# --------------------------
class ChannelMessageForm(forms.ModelForm):
    class Meta:
        model = ChannelMessage
        fields = ["text", "file", "message_type"]
        widgets = {
            "text": forms.Textarea(attrs={
                "class": "w-full p-2 border rounded-lg",
                "rows": 2,
                "placeholder": "📝 متن پیام..."
            }),
            "file": forms.ClearableFileInput(attrs={"class": "mt-2"}),
            "message_type": forms.HiddenInput(),  # مخفی برای تعیین نوع پیام
        }

    def clean(self):
        cleaned_data = super().clean()
        text = cleaned_data.get("text")
        if not text and not cleaned_data.get("file"):
            raise forms.ValidationError("باید حداقل یک متن یا فایل وارد کنید.")
        return cleaned_data

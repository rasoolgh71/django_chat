from django import forms
from .models import Conversation, Channel, ChannelMessage, CustomUser

# ------------------------------------------
# Form for creating a new 1-on-1 conversation
# ------------------------------------------
class ConversationForm(forms.ModelForm):
    class Meta:
        model = Conversation
        fields = ["user1", "user2"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            # Exclude the current user from both user selection fields
            self.fields["user1"].queryset = CustomUser.objects.exclude(pk=user.pk)
            self.fields["user2"].queryset = CustomUser.objects.exclude(pk=user.pk)

            # Pre-select and hide the current user as user1
            self.fields["user1"].initial = user
            self.fields["user1"].widget = forms.HiddenInput()


# ------------------------------------------
# Form for creating a new chat channel
# ------------------------------------------
class ChannelCreateForm(forms.ModelForm):
    class Meta:
        model = Channel
        fields = ["name", "description", "username", "image"]

    def clean_username(self):
        username = self.cleaned_data["username"]
        if not username:
            raise forms.ValidationError("Please enter a channel username.")
        if Channel.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username


# ------------------------------------------
# Form for sending a message in a channel
# ------------------------------------------
class ChannelMessageForm(forms.ModelForm):
    class Meta:
        model = ChannelMessage
        fields = ["text", "file", "message_type"]
        widgets = {
            "text": forms.Textarea(attrs={
                "class": "w-full p-2 border rounded-lg",
                "rows": 2,
                "placeholder": "📝 Enter your message..."
            }),
            "file": forms.ClearableFileInput(attrs={"class": "mt-2"}),
            "message_type": forms.HiddenInput(),  # Hidden input to store message type
        }

    def clean(self):
        """Ensure at least text or file is provided"""
        cleaned_data = super().clean()
        text = cleaned_data.get("text")
        file = cleaned_data.get("file")
        if not text and not file:
            raise forms.ValidationError("You must provide either text or a file.")
        return cleaned_data

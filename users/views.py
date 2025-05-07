from django.shortcuts import render, redirect
from django.views.generic import CreateView, UpdateView, ListView, TemplateView, View
from django.contrib.auth.views import LoginView
from chat_project.log import log
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib.auth import logout

# Create your views here.


class UserLoginView(LoginView):
    """
    برای لاگین شدن کاربر ب ایوزر نیم و پسوردد

    """
    template_name = 'login/login.html'

    def get_form(self, form_class=None):

        form = super().get_form(form_class)
        form.error_messages = {
            "invalid_login": "نام کاربری یا رمز عبور اشتباه !",

        }

        form.fields['username'].required = True
        form.fields['username'].widget.attrs = {'class': 'form-control', 'placeholder': 'نام کاربری',
                                                'autocomplete': 'off'}
        form.fields['username'].error_messages = {
            'required': 'نام کاربری را وارد کنید'
        }

        form.fields['password'].required = True
        form.fields['password'].widget.attrs = {'class': 'form-control form-control-last', 'placeholder': 'رمز عبور',
                                                'type': 'password'}
        form.fields['password'].error_messages = {
            'required': 'رمز عبور را وارد کنید'
        }

        return form

    def form_valid(self, form):
        """
        برای لاگ کردن ورود کاربر استفاده میشود

        Arguments:
            form:
                فرم ارسال شده است
        """
        res = super().form_valid(form)
        log(self.request.user, 1, 1, True, self.request)
        return res


@login_required
def user_logout(request):

    request.user.last_logout = timezone.now()
    request.user.last_activity = timezone.now()
    request.user.save()
    log(request.user, 1, 2, True, request)
    logout(request)
    return redirect('/')
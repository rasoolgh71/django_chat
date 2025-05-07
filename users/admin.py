from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from Chat_app.models import CustomUser
from django.utils.translation import gettext_lazy as _
# Register your models here.


class CustomUserAdmin(UserAdmin):
    # form = UserChangeForm
    model = CustomUser
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('first_name', 'last_name','email')}),
    )

    def save_model(self, request, obj, form, change):
        """ذخیره‌ی امن رمز عبور در هنگام ایجاد یا ویرایش کاربر"""

        """ذخیره‌ی امن رمز عبور در هنگام ایجاد یا ویرایش کاربر"""
        print("fdsf")
        if change:
            # pass# بررسی می‌کنیم که آیا این یک ویرایش است یا خیر
            old_password = CustomUser.objects.get(pk=obj.pk).password  # رمز قبلی را دریافت می‌کنیم
            if "password" in form.changed_data:  # اگر رمز جدید وارد شده باشد

                obj.set_password(form.cleaned_data["password"])#  # رمز جدید را هش کن
            else:
                pass
                # obj.password = old_password #رمز قبلی را حفظ کن
        else:
            obj.set_password(form.cleaned_data["password1"])  # برای کاربر جدید

        super().save_model(request, obj, form, change)


try:
    admin.site.unregister(CustomUser)  # اگر ثبت شده باشد، آن را حذف می‌کند
except admin.sites.NotRegistered:
    pass  # اگر قبلاً ثبت نشده بود،
admin.site.register(CustomUser, CustomUserAdmin)

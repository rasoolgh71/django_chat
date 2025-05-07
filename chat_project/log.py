from logs.models import Log


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log(user, priority, action, status,request, my_object=None,text=None, title='سفارشی'):
    """
    برای لاگ کردن است

    Arguments:
        user:
            کاربری که لاگ را رقم زده است
        priority:
            اولویت لاگ است
        action:
            عملیات را مشخص میکند
        status:
            وضعیت موفق یا ناموفق بودن لاگ را مشخص میکند
        my_object:
            در صورتی که لاگ برای یک رکورد از پایگاه داده اتفاق افتاده باشد
            آنرا دریافت میکند
    """
    lg = Log()

    lg.user = user
    lg.priority = priority
    lg.status = status
    lg.ip = get_client_ip(request)

    if text:
        lg.title = title
        lg.description = text
    else:

        if action == 1:
            lg.title = 'ورود به سامانه'
            lg.description = 'کاربر ' + str(user.username) + ' به سامانه وارد شد.'
        elif action == 2:
            lg.title = 'خروج از سامانه'
            lg.description = 'کاربر ' + str(user.username) + ' از سامانه خارج شد.'
        elif action == 3:
            lg.title = 'ایجاد رکورد'
            lg.description = "کاربر " + str(user.username) + " در" + str(my_object._meta.verbose_name) + "'" + str(
                my_object) + "'" + " را اضافه کرد."
        elif action == 4:
            lg.title = 'ویرایش رکورد'
            lg.description = "کاربر " + str(user.username) + " در" + str(my_object._meta.verbose_name) + "'" + str(
                my_object) + "'" + " را ویرایش کرد."
        elif action == 5:
            lg.title = 'حذف رکورد'
            lg.description = "کاربر " + str(user.username) + " در" + str(my_object._meta.verbose_name) + "'" + str(
                my_object) + "'" + " را حذف کرد."

    lg.save()


def log_register(title, type):
    """
    برای لاگ قسمت ثبت اطلاعات است

    Arguments:
        title:
            عنوان لاگ را مشخص میکند
        type:
            نوع اطلاعات را مشخص می کند
    """
    lg = Log()

    lg.priority = 2
    lg.status = True

    lg.title = 'ثبت اطلاعات'
    lg.description = ' یک ' + str(type) + ' با عنوان ' + str(title) + " ثبت شد."

    lg.save()

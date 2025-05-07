from django.contrib.auth.decorators import login_required
from django.views import View
from django.db.models import F, Q, Value
from django.core.paginator import Paginator
from django.http import JsonResponse, Http404, HttpResponse
from django.contrib.auth.mixins import PermissionRequiredMixin, AccessMixin
from django.contrib.auth.models import Permission
from django.contrib import messages
from django.shortcuts import redirect
from chat_project.log import log
import re
import random
import string
import datetime
from unidecode import unidecode



MOBILE_REGEX = '(0|\+98)?([ ]|-|[()]){0,2}9[1|2|3|4]([ ]|-|[()]){0,2}(?:[0-9]([ ]|-|[()]){0,2}){8}'


class Select2(View):
    """
    کلاس اصلی select2 است

    این کلاس برای صرفه جویی در زمان برای فیلد های select که اطلاعاتشان
    را از پایگاه داده میخانند ایجاد شده است و از Ajax استفاده میکند و همچنین
    قابلیت جستجو به کاربر میدهد
    """
    model = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.per_page = 20
        self.id = 'id'
        self.text = 'title'

    def get_model(self):
        if self.model is None:
            thing = User.objects.all()
            return thing
        else:
            return self.model

    def get(self, request):
        page = request.GET.get('page', 1)
        search = request.GET.get('search')

        thing = self.get_model()

        if search is not None and len(search.strip()) > 0:
            thing = thing.filter(**{self.text + '__contains': search})
        if self.id != 'id':
            thing = thing.annotate(id=F(self.id), text=self.get_text())
        else:
            thing = thing.annotate(text=self.get_text())
        thing = thing.values('id', 'text')
        paginator = Paginator(thing, self.per_page)
        results = paginator.page(int(page)).object_list
        results_bitten = list(results)
        return JsonResponse({
            'results': results_bitten,
            "pagination": {
                "more": paginator.page(page).has_next()
            }
        }, safe=False)

    def get_text(self):
        return F(self.text)


class LoginRequiredMixin(object):
    """
    این کلاس در بررسی لاگین بودن یا نبودن
    کاربر کاربرد دارد.
    """

    @classmethod
    def as_view(cls, **kwargs):
        view = super(LoginRequiredMixin, cls).as_view(**kwargs)
        return login_required(view)


class CustomDeleteView(LoginRequiredMixin, View):
    """
    این کلاس برای حذف از همه مدل ها استفاده میشود
    """
    model = None

    def get_model(self):
        """
        مدل را خالی ارسال میکند
        """
        return self.model

    def get(self, request, pk):
        """
         برای حذف کردن رکورد از جدول پایگاه داده استفاده میشود

         Arguments:
             request:
                درخواست ارسال شده به صفحه است
             pk:
                مقدار کلید اصلی رکور است
        """
        try:
            log(self.request.user, 3, 5, True, self.request, self.get_model().objects.get(pk=pk))
            self.get_model().objects.get(pk=pk).delete()
            return HttpResponse(status=200)
        except:
            raise Http404


def jalali_to_gregorian(jy, jm, jd):
    if (jy > 979):
        gy = 1600
        jy -= 979
    else:
        gy = 621
    if (jm < 7):
        days = (jm - 1) * 31
    else:
        days = ((jm - 7) * 30) + 186
    days += (365 * jy) + ((int(jy / 33)) * 8) + (int(((jy % 33) + 3) / 4)) + 78 + jd
    gy += 400 * (int(days / 146097))
    days %= 146097
    if (days > 36524):
        gy += 100 * (int(--days / 36524))
        days %= 36524
        if (days >= 365):
            days += 1
    gy += 4 * (int(days / 1461))
    days %= 1461
    if (days > 365):
        gy += int((days - 1) / 365)
        days = (days - 1) % 365
    gd = days + 1
    if ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)):
        kab = 29
    else:
        kab = 28
    sal_a = [0, 31, kab, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    while (gm < 13):
        v = sal_a[gm]
        if (gd <= v):
            break
        gd -= v
        gm += 1
    return [gy, gm, gd]


def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if (gy > 1600):
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    if (gm > 2):
        gy2 = gy + 1
    else:
        gy2 = gy
    days = (365 * gy) + (int((gy2 + 3) / 4)) - (int((gy2 + 99) / 100)) + (int((gy2 + 399) / 400)) - 80 + gd + g_d_m[
        gm - 1]
    jy += 33 * (int(days / 12053))
    days %= 12053
    jy += 4 * (int(days / 1461))
    days %= 1461
    if (days > 365):
        jy += int((days - 1) / 365)
        days = (days - 1) % 365
    if (days < 186):
        jm = 1 + int(days / 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + int((days - 186) / 30)
        jd = 1 + ((days - 186) % 30)
    return [jy, jm, jd]


def date_jalali(value, mode=1):
    if value != None:
        if mode == 1:
            date_time = value.astimezone()
            if date_time.minute < 10:
                minute = '0' + str(date_time.minute)
            else:
                minute = str(date_time.minute)
            if date_time.second < 10:
                second = '0' + str(date_time.second)
            else:
                second = str(date_time.second)

            if date_time.hour < 10:
                hour = '0' + str(date_time.hour)
            else:
                hour = str(date_time.hour)
            shamsi = gregorian_to_jalali(date_time.year, date_time.month, date_time.day)
            return " {h}:{m}:{s} {year}/{month}/{day}".format(year=shamsi[0],
                                                              month=shamsi[1],
                                                              day=shamsi[2],
                                                              h=date_time.hour,
                                                              m=minute,
                                                              s=second)
        elif mode == 2:
            year, month, day = value.split('-')
            shamsi = gregorian_to_jalali(int(year), int(month), int(day))

            return "{year}/{month}/{day}".format(year=shamsi[0], month=shamsi[1], day=shamsi[2])

        elif mode == 3:
            return " {h}:{m}:{s}".format(h=0,
                                         m=0,
                                         s=0)
    else:
        return "بدون ثبت"


def custom_change_date(value, mode=1):
    """
    برای تبدیل تاریخ استفاده میشود
    تاریخ را دریافت میکند و فرمت مورد نیاز را در
    قالب خروجی مورد نظر میدهد

    Arguments:
        value(str):
            تاریخ
        mode(int):
            حالت تبدیل را مشخص میکند
    """
    # Change Str Date to Str Persian Date
    if mode == 2:
        value = str(unidecode(str(value)))
        year, month, day = value.split('-')
        date = gregorian_to_jalali(int(year), int(month), int(day))
        string_date = "{y}/{m}/{d}".format(y=date[0], m=date[1], d=date[2])
        return string_date

    # Str Persian DateTime to DjangoDateTime
    if mode == 3:
        d = unidecode(value).split(' -- ')
        y, m, day = d[0].split('/')
        hour, min = d[1].split(':')
        pdate = jalali_to_gregorian(int(y), int(m), int(day))
        date_time = datetime.datetime(int(pdate[0]), int(pdate[1]), int(pdate[2]), int(hour), int(min))
        return date_time
    # Change DjangoDateTime to PersianDateTime
    if mode == 4:
        d = str(value).split(' ')
        y, m, day = d[0].split('-')
        time = d[1].split('+')
        time = time[0].split('.')
        hour, min, sec = time[0].split(':')
        pdate = gregorian_to_jalali(int(y), int(m), int(day))
        date_time = "{y}/{m}/{d} {h}:{min}:{s}".format(y=pdate[0], m=pdate[1], d=pdate[2], h=hour, min=min, s=sec)
        return date_time
    # Change DjangoDate to PersianDate
    if mode == 18:
        d = str(value).split(' ')
        y, m, day = d[0].split('-')
        pdate = gregorian_to_jalali(int(y), int(m), int(day))
        date_time = "{y}/{m}/{d}".format(y=pdate[0], m=pdate[1], d=pdate[2])
        return date_time
    # Change DateTime To DjangoDateTime
    if mode == 5:
        d = str(value).split(' ')
        y, m, day = d[0].split('-')
        time = d[1].split('+')
        hour, min, sec = time[0].split(':')
        date_time = datetime.datetime(int(y), int(m), int(day), int(hour), int(min), int(sec))
        return date_time
    # Change Persian Date to DjangoDate
    if mode == 6:
        y, m, day = value.split('/')
        pdate = jalali_to_gregorian(int(y), int(m), int(day))
        djangodate = datetime.date(int(pdate[0]), int(pdate[1]), int(pdate[2]))
        return djangodate
    # Change DjangoDateTime to PersianMonthDay
    if mode == 7:
        monthlist = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن',
                     'اسفند']
        d = str(value).split(' ')
        y, m, day = d[0].split('-')
        pdate = gregorian_to_jalali(int(y), int(m), int(day))
        date_time = "{d} {m}".format(m=monthlist[pdate[1] - 1], d=pdate[2])
        return date_time

    # Change DjangoDateTime to PersianDateTime For Tables
    if mode == 8:
        d = str(value).split(' ')
        y, m, day = d[0].split('-')
        time = d[1].split('+')
        time = time[0].split('.')
        hour, min, sec = time[0].split(':')
        pdate = gregorian_to_jalali(int(y), int(m), int(day))
        date_time = "{h}:{min}:{s} {y}/{m}/{d}".format(y=pdate[0], m=pdate[1], d=pdate[2], h=hour, min=min, s=sec)
        return date_time

    # Change DjangoDateTime to Year
    if mode == 9:
        d = str(value).split(' ')
        y, m, day = d[0].split('-')
        time = d[1].split('+')
        time = time[0].split('.')
        pdate = gregorian_to_jalali(int(y), int(m), int(day))
        return pdate[0]

    # Change DjangoDateTime to Month
    if mode == 10:
        d = str(value).split(' ')
        y, m, day = d[0].split('-')
        time = d[1].split('+')
        time = time[0].split('.')
        pdate = gregorian_to_jalali(int(y), int(m), int(day))
        return pdate[1]

    if mode == 11:
        d = str(value).split(' ')
        y, m, day = d[0].split('-')
        time = d[1].split('+')
        time = time[0].split('.')
        hour, min, sec = time[0].split(':')
        pdate = gregorian_to_jalali(int(y), int(m), int(day))
        date_time = "{y}-{m}-{d} {h}:{min}:{s}".format(y=pdate[0], m=pdate[1], d=pdate[2], h=hour, min=min, s=sec)
        return date_time

    # 1398/3 => (1398/3/31 : 23:59:59) => DjangoDateTime
    if mode == 12:
        pdate = []
        y, m = value.split('/')
        for i in [28, 29, 30, 31]:
            if jalali_to_gregorian(int(y), int(m), i)[2] != jalali_to_gregorian(int(y), int(m) + 1, 1)[2]:
                pdate = jalali_to_gregorian(int(y), int(m), i)
        djangodate = datetime.datetime(int(pdate[0]), int(pdate[1]), int(pdate[2]), 23, 59, 59)
        return djangodate

    # 1398/3 => (1398/3/1 : 00:00:00) => DjangoDateTime
    if mode == 14:
        y, m = value.split('/')
        pdate = jalali_to_gregorian(int(y), int(m), 1)
        djangodate = datetime.datetime(int(pdate[0]), int(pdate[1]), int(pdate[2]), 00, 00, 00)
        return djangodate

    # get Current Persian Date => [ 1399 , 4 , 16 ]
    if mode == 13:
        now = datetime.datetime.now()
        return gregorian_to_jalali(now.year, now.month, now.day)
    return 0


def validate_mobile(phone_number: str) -> bool:
    check = re.compile(MOBILE_REGEX)
    if check.search(phone_number) and len(phone_number) == 11:
        return True
    else:
        return False


def char_generator(size, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def is_valid_iran_code(input):
    if not re.search(r'^\d{10}$', input):
        return False

    check = int(input[9])
    s = sum([int(input[x]) * (10 - x) for x in range(9)]) % 11
    return (s < 2 and check == s) or (s >= 2 and check + s == 11)


class CustomAccessMixin(AccessMixin):
    permission_required = None

    def handle_no_permission(self):
        # messages.error(self.request, 'شما دسترسی ' + ' یا '.join(self.permission_required) + ' را ندارید')
        messages.error(self.request, 'شما دسترسی ' + Permission.objects.filter(
            codename=self.permission_required.split('.')[1]).last().name + ' را ندارید')
        return redirect('/dashboard')


class CustomPermissionRequiredMixin(CustomAccessMixin):
    """Verify that the current user has all specified permissions."""
    permission_required = None

    def get_permission_required(self):
        """
        Override this method to override the permission_required attribute.
        Must return an iterable.
        """
        if self.permission_required is None:
            raise ImproperlyConfigured(
                '{0} is missing the permission_required attribute. Define {0}.permission_required, or override '
                '{0}.get_permission_required().'.format(self.__class__.__name__)
            )
        if isinstance(self.permission_required, str):
            perms = (self.permission_required,)
        else:
            perms = self.permission_required
        return perms

    def has_permission(self):
        """
        Override this method to customize the way permissions are checked.
        """
        if self.permission_required is False:
            return True
        if self.request.user.is_superuser:
            return True
        if self.request.user.role == None:
            return False
        else:
            return self.request.user.role.permissions.all().filter(
                codename=self.get_permission_required()[0].split('.')[1]).exists()

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission():
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)





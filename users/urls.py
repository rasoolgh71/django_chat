from django.urls import path
from users.views import *

urlpatterns = [

        path('login', UserLoginView.as_view(), name="login"),
        path('user_logout', user_logout, name='user_logout'),
        #ajax

    ]
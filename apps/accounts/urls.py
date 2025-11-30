from django.urls import path
from .views import UserCreateView, MeView

urlpatterns = [
    path('users/', UserCreateView.as_view(), name='user-create'),
    path('users/me/', MeView.as_view(), name='user-me'),
]

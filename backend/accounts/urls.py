from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView, 
    TokenRefreshView, 
    TokenBlacklistView
)

from .views.auth import RegisterView
from .views.profile import MeView
from .views.moderation import UserListView, BanUserView, UnbanUserView

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("auth/logout/", TokenBlacklistView.as_view(), name="logout"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<int:pk>/ban/", BanUserView.as_view(), name="ban-user"),
    path("users/<int:pk>/unban/", UnbanUserView.as_view(), name="unban-user"),
]
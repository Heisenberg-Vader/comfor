from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import User


class HasProfileToPost(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if request.user.role == User.Role.MODERATOR:
            return True
        return hasattr(request.user, "profile")
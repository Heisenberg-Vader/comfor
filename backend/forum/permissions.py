from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import User


class HasProfileToPost(BasePermission):
    def has_permission(self, request, view): # Runs before the view has loaded
        if request.method in SAFE_METHODS:
            return True
        if request.user.role == User.Role.MODERATOR:
            return True
        return hasattr(request.user, "profile")
    

class IsAuthorOrModerator(BasePermission):
    message = "Only author or moderator are allowed to do this."
    
    def has_object_permission(self, request, view, obj): # Runs after the view has loaded
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.author or request.user.role == User.Role.MODERATOR
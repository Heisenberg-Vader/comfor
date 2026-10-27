from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, StudentProfile, Ban


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Platform", {"fields": ("phone", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("email", "role")}),
    )
    list_display = ("email", "username", "role", "is_active")
    

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("rollno", "user", "year", "programme")
    list_filter = ("year", "programme")
    search_fields = ("rollno", "user__email")
    

@admin.register(Ban)
class BanAdmin(admin.ModelAdmin):
    list_display = ("user", "moderator", "banned_at", "unbanned_at")
    search_fields = ("user__admin",)
    
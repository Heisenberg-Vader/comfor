from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model that serves as login table for platform."""
    
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    
    class Role(models.TextChoices):
        STUDENT = "student"
        MODERATOR = "moderator"
        
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    
    def __str__(self):
        return self.email
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]


class StudentProfile(models.Model):
    """Defines the fields for the students signing up on app"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    rollno = models.CharField(max_length=15, unique=True)
    year = models.PositiveSmallIntegerField(choices=[(i, f"Year {i}") for i in range(1, 6)])
    
    class Programme(models.TextChoices):
        BTECH_CSE = "btech_cse", "B.Tech CSE"
        BTECH_CCE = "btech_cce", "B.Tech CCE"
        BTECH_ECE = "btech_ece", "B.Tech ECE"
        BTECH_MME = "btech_mme", "B.Tech MME"
        BTECH_AIDS = "btech_aids", "B.Tech AIDS"
        
    programme = models.CharField(max_length=30, choices=Programme.choices)
    
    def __str__(self):
        return self.rollno
    

class Ban(models.Model):
    """Define fields for banned users"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bans")
    moderator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="bans_issued")
    reason = models.TextField()
    banned_at = models.DateTimeField(auto_now_add=True)
    unbanned_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user} banned at {self.banned_at:%d-%m-%Y}"
    
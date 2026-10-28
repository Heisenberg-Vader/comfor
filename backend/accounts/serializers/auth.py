from django.db import transaction
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers 

from ..models import YEAR_CHOICES, User, StudentProfile


class RegisterSerializer(serializers.ModelSerializer):
    """Validates registration data and creates a user account together with its student profile."""
    
    rollno = serializers.CharField(max_length=15, write_only=True)
    year = serializers.ChoiceField(choices=YEAR_CHOICES, write_only=True)
    programme = serializers.ChoiceField(
        choices=StudentProfile.Programme.choices, write_only=True
    )
    
    class Meta:
        model = User
        fields = ["id", "email", "username", "password", "phone", "rollno", "year", "programme"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "password": {"write_only": True},
        }
        
    def validate_phone(self, value):
        return value or None
    
    def validate_rollno(self, value):
        if StudentProfile.objects.filter(rollno=value).exists():
            raise serializers.ValidationError("This roll number already exists.")
        return value
        
    def validate(self, attrs):
        candidate = User(username=attrs["username"], email=attrs["email"])
        try:
            password_validation.validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return attrs
        
    def create(self, validated_data):
        profile_data = {
            "rollno": validated_data.pop("rollno"),
            "year": validated_data.pop("year"),
            "programme": validated_data.pop("programme"),
        }
        with transaction.atomic():
            user = User.objects.create_user(**validated_data)
            StudentProfile.objects.create(user=user, **profile_data)
        return user
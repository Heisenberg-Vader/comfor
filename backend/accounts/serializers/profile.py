from django.db import transaction
from rest_framework import serializers

from ..models import YEAR_CHOICES, User, StudentProfile


class MeSerializer(serializers.ModelSerializer):
    rollno = serializers.CharField(source="profile.rollno", read_only=True)
    year = serializers.ChoiceField(source="profile.year", choices=YEAR_CHOICES)
    programme = serializers.ChoiceField(
        source="profile.programme", choices=StudentProfile.Programme.choices
    )
    
    class Meta:
        model = User
        fields = ["id", "email", "username", "first_name", "last_name", "phone",
                  "role", "rollno", "year", "programme"]
        read_only_fields = ["id", "role", "rollno", "email", "username"]
        
    def validate_phone(self, value):
        return value or None
        
    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        return instance
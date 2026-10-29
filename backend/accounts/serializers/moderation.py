from rest_framework import serializers

from ..models import User


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "role", "is_active"]
        read_only_fields = fields
        

class BanSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)
from rest_framework import serializers

from ..models import Vote


class VoteSerializer(serializers.Serializer):
    value = serializers.ChoiceField(choices=Vote.Value.choices)
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Ban, User
from ..permissions import IsModerator
from ..serializers.moderation import BanSerializer, UserSummarySerializer


class UserListView(ListAPIView):
    serializer_class = UserSummarySerializer
    permission_classes = [IsModerator]
    
    def get_queryset(self):
        queryset = User.objects.order_by("id")
        banned = self.request.query_params.get("banned")
        if banned == "true":
            queryset = queryset.filter(is_active=False)
        elif banned == "false":
            queryset = queryset.filter(is_active=True)
        return queryset
    

class BanUserView(APIView):
    permission_classes = [IsModerator]
    
    def post(self, request, pk):
        serializer = BanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            target = get_object_or_404(User.objects.select_for_update(), pk=pk)
            
            if target.role == User.Role.MODERATOR or target.is_superuser:
                return Response(
                    {"detail": "You cannot ban a moderator or administrator."}, 
                    status=status.HTTP_403_FORBIDDEN,
                )
                
            if not target.is_active:
                return Response(
                    {"detail": "User is already banned."}, 
                    status=status.HTTP_409_CONFLICT,
                )
            
            Ban.objects.create(
                user=target,
                moderator=request.user,
                reason=serializer.validated_data["reason"],
            )
            target.is_active = False
            target.save(update_fields=["is_active"])
            
        return Response({"detail": "User has been banned."}, status=status.HTTP_200_OK)
    
    
class UnbanUserView(APIView):
    permission_classes = [IsModerator]
    
    def post(self, request, pk):
        with transaction.atomic():
            target = get_object_or_404(User.objects.select_for_update(), pk=pk)
            ban = target.bans.filter(unbanned_at__isnull=True).order_by("-banned_at").first()
            
            if ban is None:
                return Response(
                    {"detail": "User is not currently banned."}, 
                    status=status.HTTP_409_CONFLICT,
                )
                
            ban.unbanned_at = timezone.now()
            ban.save(update_fields=["unbanned_at"])
            target.is_active = True
            target.save(update_fields=["is_active"])
            
        return Response({"detail": "User has been unbanned."}, status=status.HTTP_200_OK)
            
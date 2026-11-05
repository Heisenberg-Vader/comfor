from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Post, Vote
from ..serializers.vote import VoteSerializer


def get_post_score(post):
    return post.votes.aggregate(score=Sum("value", default=0))["score"]


class VoteView(APIView):
    def put(self, request, pk):
        serializer = VoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        post = get_object_or_404(Post, pk=pk, is_deleted=False)
        vote, created = Vote.objects.update_or_create(
            user=request.user,
            post=post,
            defaults={"value": serializer.validated_data["value"]}
        )
        
        return Response(
            {"value": vote.value, "score": get_post_score(post)},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
    
    def delete(self, request, pk):
        post = get_object_or_404(Post, pk=pk, is_deleted=False)
        Vote.objects.filter(user=request.user, post=post).delete()
        return Response({"value": None, "score": get_post_score(post)})
        
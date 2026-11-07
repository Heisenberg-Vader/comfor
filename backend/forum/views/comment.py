from django.db.models import Sum, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import DestroyAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Comment, CommentVote, Post
from ..permissions import HasProfileToPost, IsAuthorOrModerator
from ..serializers.comment import CommentSerializer
from ..serializers.vote import VoteSerializer


def get_comment_score(comment):
    return comment.votes.aggregate(score=Sum("value", default=0))["score"]


class PostCommentsMixin:
    """A mixin class for only adding helper methods."""
    def get_post(self):
        return get_object_or_404(Post, pk=self.kwargs["pk"], is_deleted=False)


class CommentListCreateView(PostCommentsMixin, ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, HasProfileToPost]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["post"] = self.get_post()
        return context
    
    def get_queryset(self):
        replies = (
            Comment.objects.filter(is_deleted=False)
            .select_related("author")
            .annotate(score=Sum("votes__value", default=0))
            .order_by("-created_at")
        )
        return (
            Comment.objects.filter(post=self.get_post(), parent__isnull=True, is_deleted=False)
            .select_related("author")
            .annotate(score=Sum("votes__value", default=0))
            .prefetch_related(Prefetch("replies", queryset=replies, to_attr="visible_replies"))
        )
        
    def perform_create(self, serializer):
        comment = serializer.save(author=self.request.user, post=self.get_post())
        comment.score = 0
        comment.visible_replies = []
        

class CommentDetailView(PostCommentsMixin, DestroyAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsAuthorOrModerator]
    lookup_url_kwarg = "comment_pk" # Tells DRF to look at comment-"pk", 
    # otherwise it may mistaken the post id for comment id.
    
    def get_queryset(self):
        return Comment.objects.filter(post=self.get_post(), is_deleted=False)
        
    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])
        

class CommentVoteView(APIView):
    def get_comment(self, pk, comment_pk):
        return get_object_or_404(
            Comment,
            pk=comment_pk,
            post_id=pk,
            post__is_deleted=False,
            is_deleted=False,
        )
        
    def put(self, request, pk, comment_pk):
        serializer = VoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        comment = self.get_comment(pk, comment_pk)
        vote, created = CommentVote.objects.update_or_create(
            user=request.user,
            comment=comment,
            defaults={"value": serializer.validated_data["value"]}
        )
        
        return Response(
            {"value": vote.value, "score": get_comment_score(comment)},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
    
    def delete(self, request, pk, comment_pk):
        comment = self.get_comment(pk, comment_pk)
        CommentVote.objects.filter(user=request.user, comment=comment).delete()
        return Response({"value": None, "score": get_comment_score(comment)})
        
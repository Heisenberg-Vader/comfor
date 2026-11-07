from django.db.models import Count, IntegerField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce

from .models import Comment, CommentVote, Post, Vote


def post_queryset(user):
    my_vote = Vote.objects.filter(post=OuterRef("pk"), user=user).values("value")[:1]
    comment_count = (
        Comment.objects.filter(post=OuterRef("pk"), is_deleted=False)
        .order_by()
        .values("post")
        .annotate(total=Count("id"))
        .values("total")
    )
    return (
        Post.objects.filter(is_deleted=False)
        .select_related("author")
        .prefetch_related("images")
        .annotate(
            score=Sum("votes__value", default=0),
            my_vote=Subquery(my_vote),
            comment_count=Coalesce(Subquery(comment_count, output_field=IntegerField()), 0),   
        )
    )
    
def comment_queryset(user):
    my_vote = CommentVote.objects.filter(comment=OuterRef("pk"), user=user).values("value")[:1]
    return (
        Comment.objects.filter(is_deleted=False)
        .select_related("author")
        .annotate(
            score=Sum("votes__value", default=0),
            my_vote=Subquery(my_vote),
        )
    )
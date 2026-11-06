from django.db.models import Sum

from .models import Post


def post_queryset():
    return (
        Post.objects.filter(is_deleted=False)
        .select_related("author")
        .prefetch_related("images")
        .annotate(score=Sum("votes__value", default=0))
    )
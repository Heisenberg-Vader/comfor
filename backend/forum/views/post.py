from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated

from ..models import Post
from ..permissions import HasProfileToPost
from ..serializers.post import PostSerializer


class PostListCreateView(ListCreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated, HasProfileToPost]
    
    def get_queryset(self):
        queryset = (
            Post.objects.filter(is_deleted=False)
            .select_related("author")
            .prefetch_related("images")
        )
        year = self.request.query_params.get("year")
        
        if year is not None:
            if not year.isdigit():
                raise ValidationError({"error": "Year must be an integer."})
            queryset = queryset.filter(author_year=int(year))
        return queryset
    
    def perform_create(self, serializer):
        profile = getattr(self.request.user, "profile", None)
        serializer.save(author=self.request.user, author_year=profile.year if profile else None)
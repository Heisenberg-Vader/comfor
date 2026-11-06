from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView, RetrieveDestroyAPIView
from rest_framework.permissions import IsAuthenticated

from ..permissions import HasProfileToPost, IsAuthorOrModerator
from ..serializers.post import PostSerializer
from ..queries import post_queryset


SORT_ORDERS = {
    "new": ["-created_at"],
    "top": ["-score", "-created_at"],
}


class PostListCreateView(ListCreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated, HasProfileToPost]
    
    def get_queryset(self):
        queryset = post_queryset()
        year = self.request.query_params.get("year")
        
        if year is not None:
            if not year.isdigit():
                raise ValidationError({"year": "Year must be an integer."})
            queryset = queryset.filter(author_year=int(year))
        
        sort = self.request.query_params.get("sort", "new")
        ordering = SORT_ORDERS.get(sort)
        if ordering is None:
            raise ValidationError({"sort": "Sort must be either `new` or `top`"})
        queryset = queryset.order_by(*ordering)
        
        return queryset
    
    def perform_create(self, serializer):
        profile = getattr(self.request.user, "profile", None)
        serializer.save(author=self.request.user, author_year=profile.year if profile else None)
        
        
class PostDetailView(RetrieveDestroyAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated, IsAuthorOrModerator]
    
    def get_queryset(self):
        return post_queryset()
    
    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])
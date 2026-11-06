from django.urls import path

from .views.post import PostListCreateView, PostDetailView
from .views.vote import VoteView

urlpatterns = [
    path("posts/", PostListCreateView.as_view(), name="post-list"),
    path("posts/<int:pk>/vote/", VoteView.as_view(), name="post-vote"),
    path("posts/<int:pk>/", PostDetailView.as_view(), name="post-detail"),
]
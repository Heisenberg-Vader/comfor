from django.urls import path

from .views.post import PostListCreateView, PostDetailView
from .views.vote import VoteView
from .views.comment import CommentListCreateView, CommentDetailView, CommentVoteView

urlpatterns = [
    path("posts/", PostListCreateView.as_view(), name="post-list"),
    path("posts/<int:pk>/vote/", VoteView.as_view(), name="post-vote"),
    path("posts/<int:pk>/", PostDetailView.as_view(), name="post-detail"),
    path("posts/<int:pk>/comments/", CommentListCreateView.as_view(), name="post-comments"),
    path("posts/<int:pk>/comments/<int:comment_pk>/", CommentDetailView.as_view(), name="post-comment-detail"),
    path("posts/<int:pk>/comments/<int:comment_pk>/vote/", CommentVoteView.as_view(), name="post-comment-vote"),
]
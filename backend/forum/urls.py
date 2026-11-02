from django.urls import path

from .views.post import PostListCreateView


urlpatterns = [
    path("posts/", PostListCreateView.as_view(), name="post-list"),
]
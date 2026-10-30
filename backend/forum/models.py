from django.db import models
from django.conf import settings

from accounts.models import YEAR_CHOICES


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="posts",
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    author_year = models.PositiveSmallIntegerField(
        null=True, blank=True,
        choices=YEAR_CHOICES,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ["-created_at"]
        

class Image(models.Model):
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        related_name="images"
    )
    file = models.ImageField(upload_to="post_images/")
    
    def __str__(self):
        return f"Image for post: {self.post.title}"
    

class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments"
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Comment by {self.author} on post: {self.post.title}"
    
    class Meta:
        ordering = ["created_at"]


class Vote(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    
    class Value(models.IntegerChoices):
        UPVOTE = 1, "Upvote"
        DOWNVOTE = -1, "Downvote"
    
    value = models.SmallIntegerField(choices=Value.choices)
    voted_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Vote by {self.user} on post: {self.post.title}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "post"],
                name="unique_vote_per_user_post",
            ),
        ]
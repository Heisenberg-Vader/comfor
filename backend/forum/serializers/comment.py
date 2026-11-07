from rest_framework import serializers

from ..models import Comment


class ReplySerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", read_only=True)
    score = serializers.IntegerField(read_only=True)
    my_vote = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Comment
        fields = ["id", "author", "body", "created_at", "score", "my_vote"]


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", read_only=True)
    score = serializers.IntegerField(read_only=True)
    replies = ReplySerializer(source="visible_replies", many=True, read_only=True)
    my_vote = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Comment
        fields = ["id", "author", "body", "created_at", "parent", "score", "replies", "my_vote"]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {"body": {"max_length": 10000}}
        
    def validate_parent(self, parent):
        if parent is None:
            return parent
        post = self.context["post"]
        if parent.post_id != post.id or parent.is_deleted:
            raise serializers.ValidationError("Comment not found on this post.")
        if parent.parent_id is not None:
            raise serializers.ValidationError("You can't reply to a reply.")
        return parent
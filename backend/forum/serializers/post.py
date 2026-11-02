from django.db import transaction
from rest_framework import serializers

from ..models import Image, Post


MAX_IMAGES = 3
MAX_IMAGE_SIZE = 2 * 1024 * 1024

class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ["id", "file"]
        

class PostSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", read_only=True)
    images = ImageSerializer(many=True, read_only=True)
    image_files = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
    )
    
    class Meta:
        model = Post
        fields = ["id", "author", "title", "body", "author_year", "created_at", "images", "image_files"]
        read_only_fields = ["id", "author", "author_year", "created_at"]
    
    
    def validate_image_files(self, value):
        if len(value) > MAX_IMAGES:
            raise serializers.ValidationError(f"You can upload a maximum of {MAX_IMAGES} images.")
        
        for image in value:
            if image.size > MAX_IMAGE_SIZE:
                raise serializers.ValidationError(f"Each image must be less than {MAX_IMAGE_SIZE // (1024 * 1024)} MB.")
        
        return value
    
    def create(self, validated_data):
        image_files = validated_data.pop("image_files", [])
        
        with transaction.atomic():
            post = Post.objects.create(**validated_data)
            for image_file in image_files:
                Image.objects.create(post=post, file=image_file)
        
        return post
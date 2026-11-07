from django.contrib import admin

from .models import Post, Image, Comment, Vote, CommentVote


class ImageInline(admin.TabularInline):
    model = Image
    extra = 0
    

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "author_year", "created_at", "is_deleted")
    list_filter = ("author_year", "is_deleted")
    inlines = [ImageInline, CommentInline]
    
    
admin.site.register(Image)
admin.site.register(Comment)
admin.site.register(Vote)
admin.site.register(CommentVote)
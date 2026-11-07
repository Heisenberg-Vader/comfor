import io
import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image as PILImage
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import StudentProfile, User

from .models import Comment, CommentVote, Post, Vote

PASSWORD = "Strong@1234"
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


def make_user(username, year=None, role=User.Role.STUDENT):
    """Creates a user; passing a year also creates a student profile."""
    user = User.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password=PASSWORD,
        role=role,
    )
    if year is not None:
        StudentProfile.objects.create(
            user=user,
            rollno=f"23{username}"[:15],
            year=year,
            programme=StudentProfile.Programme.BTECH_CSE,
        )
    return user


def make_post(author, title="Title", body="Body", year=None, is_deleted=False):
    return Post.objects.create(
        author=author, title=title, body=body, author_year=year, is_deleted=is_deleted
    )


def make_comment(post, author, body="Comment", parent=None, is_deleted=False):
    return Comment.objects.create(
        post=post, author=author, body=body, parent=parent, is_deleted=is_deleted
    )


def make_image(name="test.png"):
    buffer = io.BytesIO()
    PILImage.new("RGB", (10, 10), color="red").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


# URL helpers: reverse() builds URLs from the route names in forum/urls.py
def posts_url():
    return reverse("post-list")


def post_url(post):
    return reverse("post-detail", args=[post.id])


def post_vote_url(post):
    return reverse("post-vote", args=[post.id])


def comments_url(post):
    return reverse("post-comments", args=[post.id])


def comment_url(post, comment):
    return reverse("post-comment-detail", args=[post.id, comment.id])


def comment_vote_url(post, comment):
    return reverse("post-comment-vote", args=[post.id, comment.id])


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.student = make_user("student", year=2)
        self.no_profile = make_user("noprofile")
        self.mod = make_user("mod", role=User.Role.MODERATOR)

    def test_student_with_profile_can_create_post(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(posts_url(), {"title": "Hi", "body": "There"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["author"], "student")
        self.assertEqual(response.data["author_year"], 2)
        self.assertEqual(response.data["score"], 0)
        self.assertIsNone(response.data["my_vote"])
        self.assertEqual(response.data["comment_count"], 0)
        self.assertEqual(response.data["images"], [])

    def test_client_cannot_set_author_year(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            posts_url(), {"title": "Hi", "body": "There", "author_year": 4}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.get(id=response.data["id"]).author_year, 2)

    def test_student_without_profile_cannot_create_post(self):
        self.client.force_authenticate(self.no_profile)
        response = self.client.post(posts_url(), {"title": "Hi", "body": "There"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Post.objects.exists())

    def test_moderator_without_profile_can_create_post(self):
        self.client.force_authenticate(self.mod)
        response = self.client.post(posts_url(), {"title": "Hi", "body": "There"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["author_year"])

    def test_unauthenticated_cannot_create_post(self):
        response = self.client.post(posts_url(), {"title": "Hi", "body": "There"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_title_and_body_are_required(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(posts_url(), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)
        self.assertIn("body", response.data)

    def test_create_post_with_images(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            posts_url(),
            {"title": "Hi", "body": "There", "image_files": [make_image("a.png"), make_image("b.png")]},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["images"]), 2)
        self.assertIn("post_images/", response.data["images"][0]["file"])

    def test_too_many_images_rejected(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            posts_url(),
            {"title": "Hi", "body": "There", "image_files": [make_image(f"{i}.png") for i in range(4)]},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image_files", response.data)
        self.assertFalse(Post.objects.exists())

    def test_oversized_image_rejected(self):
        self.client.force_authenticate(self.student)
        # Lower the limit for this test instead of building a real 2 MB image
        with patch("forum.serializers.post.MAX_IMAGE_SIZE", 10):
            response = self.client.post(
                posts_url(),
                {"title": "Hi", "body": "There", "image_files": [make_image()]},
                format="multipart",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image_files", response.data)

    def test_non_image_file_rejected(self):
        self.client.force_authenticate(self.student)
        fake = SimpleUploadedFile("fake.png", b"not an image", content_type="image/png")
        response = self.client.post(
            posts_url(),
            {"title": "Hi", "body": "There", "image_files": [fake]},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image_files", response.data)


class PostFeedTests(APITestCase):
    def setUp(self):
        self.student = make_user("student", year=2)
        self.other = make_user("other", year=4)
        self.client.force_authenticate(self.student)

    def results(self, response):
        return response.data["results"]

    def test_unauthenticated_cannot_read_feed(self):
        self.client.force_authenticate(None)
        response = self.client.get(posts_url())

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_profile_can_read_feed(self):
        self.client.force_authenticate(make_user("noprofile"))
        response = self.client.get(posts_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_feed_excludes_deleted_posts(self):
        visible = make_post(self.student)
        make_post(self.student, is_deleted=True)
        response = self.client.get(posts_url())

        ids = [post["id"] for post in self.results(response)]
        self.assertEqual(ids, [visible.id])

    def test_default_order_is_newest_first(self):
        first = make_post(self.student, title="first")
        second = make_post(self.student, title="second")
        response = self.client.get(posts_url())

        ids = [post["id"] for post in self.results(response)]
        self.assertEqual(ids, [second.id, first.id])

    def test_sort_top_orders_by_score_then_newest(self):
        low = make_post(self.student, title="low")
        high = make_post(self.student, title="high")
        tie = make_post(self.student, title="tie")
        Vote.objects.create(user=self.student, post=high, value=1)
        Vote.objects.create(user=self.other, post=high, value=1)
        Vote.objects.create(user=self.student, post=low, value=1)
        Vote.objects.create(user=self.student, post=tie, value=1)
        response = self.client.get(posts_url(), {"sort": "top"})

        ids = [post["id"] for post in self.results(response)]
        # high has 2; tie and low have 1 each, so the newer one (tie) comes first
        self.assertEqual(ids, [high.id, tie.id, low.id])

    def test_invalid_sort_rejected(self):
        response = self.client.get(posts_url(), {"sort": "abc"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sort", response.data)

    def test_year_filter(self):
        second_year = make_post(self.student, year=2)
        make_post(self.other, year=4)
        response = self.client.get(posts_url(), {"year": 2})

        ids = [post["id"] for post in self.results(response)]
        self.assertEqual(ids, [second_year.id])

    def test_invalid_year_rejected(self):
        response = self.client.get(posts_url(), {"year": "abc"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("year", response.data)

    def test_score_counts_up_and_down_votes(self):
        post = make_post(self.student)
        third = make_user("third", year=1)
        Vote.objects.create(user=self.student, post=post, value=1)
        Vote.objects.create(user=self.other, post=post, value=1)
        Vote.objects.create(user=third, post=post, value=-1)
        response = self.client.get(posts_url())

        self.assertEqual(self.results(response)[0]["score"], 1)

    def test_comment_count_includes_replies_and_skips_deleted(self):
        post = make_post(self.student)
        top = make_comment(post, self.student)
        make_comment(post, self.other, parent=top)
        make_comment(post, self.other, is_deleted=True)
        response = self.client.get(posts_url())

        self.assertEqual(self.results(response)[0]["comment_count"], 2)

    def test_score_and_comment_count_do_not_inflate_each_other(self):
        # Guards against the double-join bug: 3 votes x 2 comments must not give 6
        post = make_post(self.student)
        third = make_user("third", year=1)
        for user in (self.student, self.other, third):
            Vote.objects.create(user=user, post=post, value=1)
        make_comment(post, self.student)
        make_comment(post, self.other)
        response = self.client.get(posts_url())

        self.assertEqual(self.results(response)[0]["score"], 3)
        self.assertEqual(self.results(response)[0]["comment_count"], 2)

    def test_my_vote_reflects_the_current_user(self):
        post = make_post(self.other)
        Vote.objects.create(user=self.student, post=post, value=-1)

        response = self.client.get(posts_url())
        self.assertEqual(self.results(response)[0]["my_vote"], -1)

        self.client.force_authenticate(self.other)
        response = self.client.get(posts_url())
        self.assertIsNone(self.results(response)[0]["my_vote"])

    def test_feed_is_paginated(self):
        for i in range(21):
            make_post(self.student, title=f"post {i}")
        response = self.client.get(posts_url())

        self.assertEqual(response.data["count"], 21)
        self.assertEqual(len(self.results(response)), 20)
        self.assertIsNotNone(response.data["next"])


class PostDetailTests(APITestCase):
    def setUp(self):
        self.author = make_user("author", year=2)
        self.other = make_user("other", year=3)
        self.mod = make_user("mod", role=User.Role.MODERATOR)
        self.post = make_post(self.author)

    def test_get_post(self):
        Vote.objects.create(user=self.other, post=self.post, value=1)
        self.client.force_authenticate(self.other)
        response = self.client.get(post_url(self.post))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.post.id)
        self.assertEqual(response.data["score"], 1)
        self.assertEqual(response.data["my_vote"], 1)

    def test_get_deleted_post_returns_404(self):
        self.post.is_deleted = True
        self.post.save()
        self.client.force_authenticate(self.other)
        response = self.client.get(post_url(self.post))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_missing_post_returns_404(self):
        self.client.force_authenticate(self.other)
        response = self.client.get(reverse("post-detail", args=[99999]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_author_can_delete_post(self):
        self.client.force_authenticate(self.author)
        response = self.client.delete(post_url(self.post))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_deleted)

    def test_other_student_cannot_delete_post(self):
        self.client.force_authenticate(self.other)
        response = self.client.delete(post_url(self.post))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.post.refresh_from_db()
        self.assertFalse(self.post.is_deleted)

    def test_moderator_can_delete_post(self):
        self.client.force_authenticate(self.mod)
        response = self.client.delete(post_url(self.post))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_deleted)

    def test_deleting_twice_returns_404(self):
        self.client.force_authenticate(self.author)
        self.client.delete(post_url(self.post))
        response = self.client.delete(post_url(self.post))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_soft_delete_keeps_the_row(self):
        self.client.force_authenticate(self.author)
        self.client.delete(post_url(self.post))

        self.assertTrue(Post.objects.filter(id=self.post.id).exists())


class PostVoteTests(APITestCase):
    def setUp(self):
        self.author = make_user("author", year=2)
        self.voter = make_user("voter", year=3)
        self.post = make_post(self.author)
        self.client.force_authenticate(self.voter)

    def test_first_upvote_creates_vote(self):
        response = self.client.put(post_vote_url(self.post), {"value": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {"value": 1, "score": 1})

    def test_same_vote_again_changes_nothing(self):
        self.client.put(post_vote_url(self.post), {"value": 1}, format="json")
        response = self.client.put(post_vote_url(self.post), {"value": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["score"], 1)
        self.assertEqual(Vote.objects.filter(user=self.voter, post=self.post).count(), 1)

    def test_switching_vote_moves_score_by_two(self):
        Vote.objects.create(user=self.author, post=self.post, value=1)
        self.client.put(post_vote_url(self.post), {"value": 1}, format="json")
        response = self.client.put(post_vote_url(self.post), {"value": -1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"value": -1, "score": 0})

    def test_delete_removes_vote(self):
        self.client.put(post_vote_url(self.post), {"value": 1}, format="json")
        response = self.client.delete(post_vote_url(self.post))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"value": None, "score": 0})
        self.assertFalse(Vote.objects.filter(user=self.voter, post=self.post).exists())

    def test_delete_without_vote_is_harmless(self):
        response = self.client.delete(post_vote_url(self.post))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["score"], 0)

    def test_invalid_vote_values_rejected(self):
        for body in ({"value": 5}, {"value": 0}, {}):
            response = self.client.put(post_vote_url(self.post), body, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, body)

    def test_vote_on_deleted_post_returns_404(self):
        self.post.is_deleted = True
        self.post.save()
        response = self.client.put(post_vote_url(self.post), {"value": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_vote_on_missing_post_returns_404(self):
        response = self.client.put(reverse("post-vote", args=[99999]), {"value": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_cannot_vote(self):
        self.client.force_authenticate(None)
        response = self.client.put(post_vote_url(self.post), {"value": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CommentCreateAndListTests(APITestCase):
    def setUp(self):
        self.student = make_user("student", year=2)
        self.other = make_user("other", year=3)
        self.post = make_post(self.student)
        self.client.force_authenticate(self.student)

    def results(self, response):
        return response.data["results"]

    def test_create_top_level_comment(self):
        response = self.client.post(comments_url(self.post), {"body": "hello"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["author"], "student")
        self.assertIsNone(response.data["parent"])
        self.assertEqual(response.data["score"], 0)
        self.assertIsNone(response.data["my_vote"])
        self.assertEqual(response.data["replies"], [])

    def test_same_user_can_comment_many_times(self):
        for i in range(3):
            response = self.client.post(comments_url(self.post), {"body": f"c{i}"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Comment.objects.filter(post=self.post).count(), 3)

    def test_empty_body_rejected(self):
        for body in ({"body": ""}, {}):
            response = self.client.post(comments_url(self.post), body, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, body)

    def test_comment_on_deleted_post_returns_404(self):
        self.post.is_deleted = True
        self.post.save()
        response = self.client.post(comments_url(self.post), {"body": "hi"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_comment_on_missing_post_returns_404(self):
        response = self.client.post(reverse("post-comments", args=[99999]), {"body": "hi"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_without_profile_can_read_but_not_comment(self):
        self.client.force_authenticate(make_user("noprofile"))

        response = self.client.post(comments_url(self.post), {"body": "hi"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.get(comments_url(self.post))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_in_body_is_ignored(self):
        other_post = make_post(self.other)
        response = self.client.post(
            comments_url(self.post), {"body": "hi", "post": other_post.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.get(id=response.data["id"]).post, self.post)

    def test_list_only_shows_this_posts_comments(self):
        # Regression test for the missing post filter in get_queryset()
        other_post = make_post(self.other)
        mine = make_comment(self.post, self.student)
        make_comment(other_post, self.other)
        response = self.client.get(comments_url(self.post))

        ids = [comment["id"] for comment in self.results(response)]
        self.assertEqual(ids, [mine.id])

    def test_list_excludes_deleted_comments(self):
        visible = make_comment(self.post, self.student)
        make_comment(self.post, self.student, is_deleted=True)
        response = self.client.get(comments_url(self.post))

        ids = [comment["id"] for comment in self.results(response)]
        self.assertEqual(ids, [visible.id])

    def test_top_level_comments_newest_first(self):
        first = make_comment(self.post, self.student, body="first")
        second = make_comment(self.post, self.other, body="second")
        response = self.client.get(comments_url(self.post))

        ids = [comment["id"] for comment in self.results(response)]
        self.assertEqual(ids, [second.id, first.id])

    def test_reply_is_created_and_nested(self):
        top = make_comment(self.post, self.other)
        response = self.client.post(
            comments_url(self.post), {"body": "reply", "parent": top.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["parent"], top.id)

        response = self.client.get(comments_url(self.post))
        results = self.results(response)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(results[0]["id"], top.id)
        self.assertEqual(len(results[0]["replies"]), 1)
        self.assertEqual(results[0]["replies"][0]["body"], "reply")

    def test_replies_newest_first_and_deleted_hidden(self):
        top = make_comment(self.post, self.other)
        first = make_comment(self.post, self.student, parent=top)
        second = make_comment(self.post, self.other, parent=top)
        make_comment(self.post, self.other, parent=top, is_deleted=True)
        response = self.client.get(comments_url(self.post))

        reply_ids = [reply["id"] for reply in self.results(response)[0]["replies"]]
        self.assertEqual(reply_ids, [second.id, first.id])

    def test_reply_to_reply_rejected(self):
        top = make_comment(self.post, self.other)
        reply = make_comment(self.post, self.other, parent=top)
        response = self.client.post(
            comments_url(self.post), {"body": "too deep", "parent": reply.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", response.data)

    def test_parent_from_another_post_rejected(self):
        other_post = make_post(self.other)
        foreign = make_comment(other_post, self.other)
        response = self.client.post(
            comments_url(self.post), {"body": "hi", "parent": foreign.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", response.data)

    def test_deleted_parent_rejected(self):
        top = make_comment(self.post, self.other, is_deleted=True)
        response = self.client.post(
            comments_url(self.post), {"body": "hi", "parent": top.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", response.data)

    def test_missing_parent_rejected(self):
        response = self.client.post(
            comments_url(self.post), {"body": "hi", "parent": 99999}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", response.data)


class CommentDeleteTests(APITestCase):
    def setUp(self):
        self.author = make_user("author", year=2)
        self.other = make_user("other", year=3)
        self.mod = make_user("mod", role=User.Role.MODERATOR)
        self.post = make_post(self.author)
        self.comment = make_comment(self.post, self.author)

    def test_author_can_delete_comment(self):
        self.client.force_authenticate(self.author)
        response = self.client.delete(comment_url(self.post, self.comment))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_deleted)

    def test_other_student_cannot_delete_comment(self):
        self.client.force_authenticate(self.other)
        response = self.client.delete(comment_url(self.post, self.comment))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.comment.refresh_from_db()
        self.assertFalse(self.comment.is_deleted)

    def test_moderator_can_delete_comment(self):
        self.client.force_authenticate(self.mod)
        response = self.client.delete(comment_url(self.post, self.comment))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_comment_under_wrong_post_returns_404(self):
        other_post = make_post(self.other)
        self.client.force_authenticate(self.author)
        response = self.client.delete(comment_url(other_post, self.comment))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.comment.refresh_from_db()
        self.assertFalse(self.comment.is_deleted)

    def test_deleting_twice_returns_404(self):
        self.client.force_authenticate(self.author)
        self.client.delete(comment_url(self.post, self.comment))
        response = self.client.delete(comment_url(self.post, self.comment))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deleted_reply_disappears_from_thread(self):
        reply = make_comment(self.post, self.other, parent=self.comment)
        self.client.force_authenticate(self.other)
        self.client.delete(comment_url(self.post, reply))
        response = self.client.get(comments_url(self.post))

        self.assertEqual(response.data["results"][0]["replies"], [])


class CommentVoteTests(APITestCase):
    def setUp(self):
        self.author = make_user("author", year=2)
        self.voter = make_user("voter", year=3)
        self.post = make_post(self.author)
        self.comment = make_comment(self.post, self.author)
        self.reply = make_comment(self.post, self.author, parent=self.comment)
        self.client.force_authenticate(self.voter)

    def test_vote_on_comment(self):
        response = self.client.put(comment_vote_url(self.post, self.comment), {"value": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {"value": 1, "score": 1})

    def test_vote_on_reply(self):
        response = self.client.put(comment_vote_url(self.post, self.reply), {"value": -1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {"value": -1, "score": -1})

    def test_switching_comment_vote(self):
        self.client.put(comment_vote_url(self.post, self.comment), {"value": 1}, format="json")
        response = self.client.put(comment_vote_url(self.post, self.comment), {"value": -1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"value": -1, "score": -1})
        self.assertEqual(CommentVote.objects.filter(user=self.voter, comment=self.comment).count(), 1)

    def test_removing_comment_vote_keeps_post_vote(self):
        Vote.objects.create(user=self.voter, post=self.post, value=1)
        self.client.put(comment_vote_url(self.post, self.comment), {"value": 1}, format="json")
        response = self.client.delete(comment_vote_url(self.post, self.comment))

        self.assertEqual(response.data, {"value": None, "score": 0})
        self.assertTrue(Vote.objects.filter(user=self.voter, post=self.post).exists())

    def test_invalid_vote_value_rejected(self):
        response = self.client.put(comment_vote_url(self.post, self.comment), {"value": 5}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_vote_on_comment_under_deleted_post_returns_404(self):
        self.post.is_deleted = True
        self.post.save()
        response = self.client.put(comment_vote_url(self.post, self.comment), {"value": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_vote_on_deleted_comment_returns_404(self):
        self.comment.is_deleted = True
        self.comment.save()
        response = self.client.put(comment_vote_url(self.post, self.comment), {"value": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_vote_on_comment_under_wrong_post_returns_404(self):
        other_post = make_post(self.author)
        response = self.client.put(comment_vote_url(other_post, self.comment), {"value": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_shows_scores_and_my_vote(self):
        CommentVote.objects.create(user=self.voter, comment=self.comment, value=1)
        CommentVote.objects.create(user=self.author, comment=self.comment, value=1)
        CommentVote.objects.create(user=self.voter, comment=self.reply, value=-1)
        response = self.client.get(comments_url(self.post))

        thread = response.data["results"][0]
        self.assertEqual(thread["score"], 2)
        self.assertEqual(thread["my_vote"], 1)
        self.assertEqual(thread["replies"][0]["score"], -1)
        self.assertEqual(thread["replies"][0]["my_vote"], -1)

    def test_my_vote_is_null_for_someone_who_has_not_voted(self):
        CommentVote.objects.create(user=self.voter, comment=self.comment, value=1)
        self.client.force_authenticate(self.author)
        response = self.client.get(comments_url(self.post))

        self.assertIsNone(response.data["results"][0]["my_vote"])
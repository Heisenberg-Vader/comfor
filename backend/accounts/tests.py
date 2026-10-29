from rest_framework import status
from rest_framework.test import APITestCase

from .models import Ban, StudentProfile, User


class BanTests(APITestCase):
    def setUp(self):
        self.mod1 = User.objects.create_user(
            username="mod1", email="mod1@test.com", password="Strong@1234",
            role=User.Role.MODERATOR,
        )
        self.mod2 = User.objects.create_user(
            username="mod2", email="mod2@test.com", password="Strong@1234",
            role=User.Role.MODERATOR,
        )
        self.student = User.objects.create_user(
            username="student", email="student@test.com", password="Strong@1234",
            role=User.Role.STUDENT,
        )
        self.student1 = User.objects.create_user(
            username="student1", email="student1@test.com", password="Strong@1234",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(
            user=self.student, rollno="23ucs501", year=4, programme="btech_cse",
        )
        StudentProfile.objects.create(
            user=self.student1, rollno="23ucs511", year=4, programme="btech_cse",
        )
        
    def test_moderator_not_logged_in_cannot_ban_student(self):
        response = self.client.post(
            f"/api/users/{self.student.id}/ban/",
            {"reason": "spam"},    
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)
        
    def test_moderator_can_ban_student(self):
        self.client.force_authenticate(user=self.mod1)
        response = self.client.post(
            f"/api/users/{self.student.id}/ban/",
            {"reason": "spam"},    
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)
        
    def test_moderator_can_unban_student(self):
        ban = Ban.objects.create(user=self.student, moderator=self.mod1, reason="spam")
        self.student.is_active = False
        self.student.save()

        self.client.force_authenticate(user=self.mod1)
        response = self.client.post(f"/api/users/{self.student.id}/unban/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)
        ban.refresh_from_db()
        self.assertIsNotNone(ban.unbanned_at)
        
    def test_moderator_cannot_ban_another_moderator(self):
        self.client.force_authenticate(user=self.mod1)
        response = self.client.post(
            f"/api/users/{self.mod2.id}/ban/",
            {"reason": "spam"},    
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.mod2.refresh_from_db()
        self.assertTrue(self.mod2.is_active)
        
    def test_moderator_cannot_ban_without_reason(self):
        self.client.force_authenticate(user=self.mod1)
        response = self.client.post(
            f"/api/users/{self.student.id}/ban/",
            {},    
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)
        
    def test_student_cannot_list_other_users(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_student_cannot_ban_another_student(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            f"/api/users/{self.student1.id}/ban/",
            {"reason": "spam"},    
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.student1.refresh_from_db()
        self.assertTrue(self.student1.is_active)
        
    def test_student_cannot_unban_another_student(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            f"/api/users/{self.student.id}/unban/",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)
        
    def test_moderator_cannot_ban_already_banned_student(self):
        self.client.force_authenticate(user=self.mod1)
        self.student.is_active = False
        self.student.save()
        response = self.client.post(
            f"/api/users/{self.student.id}/ban/",
            {"reason": "spam"},    
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.student.is_active = True
        self.student.save()
        
    def test_moderator_cannot_unban_not_banned_student(self):
        self.client.force_authenticate(user=self.mod1)
        response = self.client.post(
            f"/api/users/{self.student.id}/unban/",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        
        
class RegisterTests(APITestCase):
    def setUp(self):
        self.register_data = {
            "email": "student@test.com",
            "username": "student",
            "password": "Strong@1234",
            "phone": "1234567890",
            "rollno": "23ucs501",
            "year": 4,
            "programme": "btech_cse",
        }
        
        self.duplicate_rollno_data = {
            "email": "student1@test.com",
            "username": "student1",
            "password": "Strong@1234",
            "phone": "1234527890",
            "rollno": "23ucs501",
            "year": 4,
            "programme": "btech_cse",
        }
        
        self.duplicate_email_data = {
            "email": "student@test.com",
            "username": "student2",
            "password": "Strong@1234",
            "phone": "1134567890",
            "rollno": "23ucs521",
            "year": 4,
            "programme": "btech_cse",
        }
        
        self.weak_password_data = {
            "email": "student3@test.com",
            "username": "student3",
            "password": "1234",
            "phone": "1134567890",
            "rollno": "23ucs521",
            "year": 4,
            "programme": "btech_cse",
        }
    
    def test_register_student(self):
        response = self.client.post(
            "/api/auth/register/",
            data=self.register_data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.data)
        user = User.objects.get(email="student@test.com")
        self.assertTrue(user.check_password("Strong@1234"))
        self.assertEqual(user.profile.rollno, "23ucs501")
        self.assertEqual(user.role, User.Role.STUDENT)
    
    def test_register_student_with_existing_rollno(self):
        response = self.client.post(
            "/api/auth/register/",
            data=self.register_data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(
            "/api/auth/register/",
            data=self.duplicate_rollno_data,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("rollno", response.data)

    def test_register_student_with_existing_email(self):
        response = self.client.post(
            "/api/auth/register/",
            data=self.register_data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(
            "/api/auth/register/",
            data=self.duplicate_email_data,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        
    def test_register_with_weak_password(self):
        response = self.client.post(
            "/api/auth/register/",
            data=self.weak_password_data,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthenticationViewsTests(TestCase):
    def test_registration_creates_and_logs_in_user(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "ada",
                "email": "ada@example.com",
                "password1": "SafePassword123!",
                "password2": "SafePassword123!",
            },
        )

        user_model = get_user_model()
        user = user_model.objects.get(username="ada")
        self.assertRedirects(response, reverse("profile"))
        self.assertEqual(self.client.session.get("_auth_user_id"), str(user.pk))

    def test_login_accepts_valid_credentials(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="ada",
            email="ada@example.com",
            password="SafePassword123!",
        )

        response = self.client.post(
            reverse("login"),
            {"username": "ada", "password": "SafePassword123!"},
        )

        self.assertRedirects(response, reverse("profile"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_profile_requires_authentication(self):
        response = self.client.get(reverse("profile"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('profile')}",
        )

    def test_logout_requires_post_and_returns_home(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="ada",
            password="SafePassword123!",
        )
        self.client.force_login(user)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

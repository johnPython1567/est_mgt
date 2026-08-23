from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from .models import Favorite, Inquiry, Property


def make_property(**overrides):
    defaults = {
        "title": "Sunny Two Bedroom Flat",
        "slug": "sunny-two-bedroom-flat",
        "description": "A bright flat close to the market.",
        "property_type": "apartment",
        "listing_type": "rent",
        "price": "150000.00",
        "bedrooms": 2,
        "bathrooms": 1,
        "area": 85,
        "address": "12 Marina Road",
        "city": "Lagos",
        "state": "Lagos",
        "is_published": True,
    }
    defaults.update(overrides)
    return Property.objects.create(**defaults)


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



class PropertyModelTests(TestCase):
    def test_string_representation_is_title(self):
        property_obj = make_property()
        self.assertEqual(str(property_obj), "Sunny Two Bedroom Flat")

    def test_get_absolute_url_uses_slug(self):
        property_obj = make_property()
        self.assertEqual(
            property_obj.get_absolute_url(),
            reverse("property-detail", args=[property_obj.slug]),
        )

    def test_slug_must_be_unique(self):
        make_property()
        with self.assertRaises(IntegrityError):
            make_property(title="Another Flat")


class FavoriteModelTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username="ada",
            password="SafePassword123!",
        )
        self.property_obj = make_property()

    def test_string_representation(self):
        favorite = Favorite.objects.create(
            user=self.user,
            property=self.property_obj,
        )
        self.assertEqual(
            str(favorite),
            "ada saved Sunny Two Bedroom Flat",
        )

    def test_user_cannot_favorite_same_property_twice(self):
        Favorite.objects.create(user=self.user, property=self.property_obj)
        with self.assertRaises(IntegrityError):
            Favorite.objects.create(user=self.user, property=self.property_obj)


class ToggleFavoriteViewTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username="ada",
            password="SafePassword123!",
        )
        self.property_obj = make_property()
        self.url = reverse("toggle-favorite", args=[self.property_obj.slug])

    def test_requires_login(self):
        response = self.client.post(self.url)
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={self.url}",
        )

    def test_requires_post(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_toggle_creates_then_removes_favorite(self):
        self.client.force_login(self.user)

        first_response = self.client.post(self.url)
        self.assertTrue(
            Favorite.objects.filter(
                user=self.user, property=self.property_obj
            ).exists()
        )
        self.assertRedirects(first_response, self.property_obj.get_absolute_url())

        second_response = self.client.post(self.url)
        self.assertFalse(
            Favorite.objects.filter(
                user=self.user, property=self.property_obj
            ).exists()
        )
        self.assertRedirects(second_response, self.property_obj.get_absolute_url())

    def test_ajax_toggle_returns_json(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.url, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["is_favorited"], True)

    def test_cannot_favorite_unpublished_property(self):
        self.property_obj.is_published = False
        self.property_obj.save()
        self.client.force_login(self.user)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)


class PropertyListViewSearchTests(TestCase):
    def setUp(self):
        self.url = reverse("property-list")

        self.cheap_apartment = make_property(
            title="Cheap Lagos Apartment",
            slug="cheap-lagos-apartment",
            property_type="apartment",
            listing_type="rent",
            price="80000.00",
            bedrooms=1,
            bathrooms=1,
            city="Lagos",
        )
        self.expensive_house = make_property(
            title="Expensive Abuja House",
            slug="expensive-abuja-house",
            property_type="house",
            listing_type="sale",
            price="50000000.00",
            bedrooms=5,
            bathrooms=4,
            city="Abuja",
        )
        self.unpublished_property = make_property(
            title="Hidden Listing",
            slug="hidden-listing",
            is_published=False,
        )

    def test_only_published_properties_are_listed(self):
        response = self.client.get(self.url)
        properties = list(response.context["properties"])
        self.assertIn(self.cheap_apartment, properties)
        self.assertNotIn(self.unpublished_property, properties)

    def test_filters_by_location(self):
        response = self.client.get(self.url, {"location": "Abuja"})
        properties = list(response.context["properties"])
        self.assertEqual(properties, [self.expensive_house])

    def test_filters_by_price_range(self):
        response = self.client.get(
            self.url, {"min_price": "1000000", "max_price": "60000000"}
        )
        properties = list(response.context["properties"])
        self.assertEqual(properties, [self.expensive_house])

    def test_filters_by_minimum_bedrooms(self):
        response = self.client.get(self.url, {"bedrooms": "3"})
        properties = list(response.context["properties"])
        self.assertEqual(properties, [self.expensive_house])

    def test_invalid_price_filter_is_ignored_not_errored(self):
        response = self.client.get(self.url, {"min_price": "not-a-number"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["selected_filters"]["min_price"])

    def test_ordering_by_price_ascending(self):
        response = self.client.get(self.url, {"ordering": "price_asc"})
        properties = list(response.context["properties"])
        self.assertEqual(
            properties, [self.cheap_apartment, self.expensive_house]
        )

    def test_pagination_splits_results_across_pages(self):
        for index in range(10):
            make_property(
                title=f"Extra Property {index}",
                slug=f"extra-property-{index}",
            )

        first_page = self.client.get(self.url)
        self.assertTrue(first_page.context["is_paginated"])
        self.assertEqual(len(first_page.context["properties"]), 9)

        second_page = self.client.get(self.url, {"page": 2})
        self.assertGreater(len(second_page.context["properties"]), 0)


class InquiryModelTests(TestCase):
    def test_string_representation(self):
        property_obj = make_property()
        inquiry = Inquiry.objects.create(
            property=property_obj,
            name="Chidi Okafor",
            email="chidi@example.com",
            message="Is this still available?",
        )
        self.assertEqual(
            str(inquiry),
            "Inquiry from Chidi Okafor about Sunny Two Bedroom Flat",
        )

    def test_default_status_is_new(self):
        property_obj = make_property()
        inquiry = Inquiry.objects.create(
            property=property_obj,
            name="Chidi Okafor",
            email="chidi@example.com",
            message="Is this still available?",
        )
        self.assertEqual(inquiry.status, "new")

    def test_deleting_user_keeps_the_inquiry(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="chidi", password="SafePassword123!"
        )
        property_obj = make_property()
        inquiry = Inquiry.objects.create(
            property=property_obj,
            user=user,
            name="Chidi Okafor",
            email="chidi@example.com",
            message="Is this still available?",
        )

        user.delete()
        inquiry.refresh_from_db()
        self.assertIsNone(inquiry.user)


class InquiryCreateViewTests(TestCase):
    def setUp(self):
        self.property_obj = make_property()
        self.url = reverse("inquiry-create")
        self.valid_payload = {
            "property": self.property_obj.slug,
            "name": "Chidi Okafor",
            "email": "chidi@example.com",
            "phone": "08012345678",
            "message": "Is this still available?",
        }

    def test_guest_can_submit_an_inquiry(self):
        response = self.client.post(self.url, self.valid_payload)

        self.assertRedirects(response, self.property_obj.get_absolute_url())
        inquiry = Inquiry.objects.get()
        self.assertIsNone(inquiry.user)
        self.assertEqual(inquiry.name, "Chidi Okafor")
        self.assertEqual(inquiry.property, self.property_obj)

    def test_logged_in_user_is_attached_to_the_inquiry(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="chidi", password="SafePassword123!"
        )
        self.client.force_login(user)

        self.client.post(self.url, self.valid_payload)

        inquiry = Inquiry.objects.get()
        self.assertEqual(inquiry.user, user)

    def test_missing_message_is_rejected(self):
        payload = dict(self.valid_payload)
        payload["message"] = ""

        response = self.client.post(self.url, payload)

        self.assertRedirects(response, self.property_obj.get_absolute_url())
        self.assertEqual(Inquiry.objects.count(), 0)

    def test_cannot_inquire_about_unpublished_property(self):
        self.property_obj.is_published = False
        self.property_obj.save()

        response = self.client.post(self.url, self.valid_payload)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Inquiry.objects.count(), 0)

    def test_get_is_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)


class ProfileInquiriesTests(TestCase):
    def test_profile_lists_only_the_current_user_inquiries(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="chidi", password="SafePassword123!"
        )
        other_user = user_model.objects.create_user(
            username="ngozi", password="SafePassword123!"
        )

        property_obj = make_property()

        own_inquiry = Inquiry.objects.create(
            property=property_obj,
            user=user,
            name="Chidi Okafor",
            email="chidi@example.com",
            message="Interested.",
        )
        Inquiry.objects.create(
            property=property_obj,
            user=other_user,
            name="Ngozi Eze",
            email="ngozi@example.com",
            message="Also interested.",
        )

        self.client.force_login(user)
        response = self.client.get(reverse("profile"))

        self.assertEqual(list(response.context["inquiries"]), [own_inquiry])
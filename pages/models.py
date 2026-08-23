from django.conf import settings
from django.db import models
from django.urls import reverse

# Create your models here.

class Property(models.Model):
        PROPERTY_TYPES = [
            ("house", "House"),
            ("apartment", "Apartment"),
            ("condo", "Condo"),
            ("townhouse", "Townhouse"),
            ("land", "Land"),
            ("commercial", "Commercial"),
            ("office", "Office"),
            ("warehouse", "Warehouse"),
        ]

        LISTING_TYPES = [
            ("sale", "For Sale"),
            ("rent", "For Rent"),
        ]

        title = models.CharField(max_length=200)
        slug = models.SlugField(unique=True)

        description = models.TextField()

        property_type = models.CharField(
            max_length=20,
            choices=PROPERTY_TYPES
        )

        listing_type = models.CharField(
            max_length=10,
            choices=LISTING_TYPES
        )

        price = models.DecimalField(
            max_digits=12,
            decimal_places=2
        )

        bedrooms = models.PositiveIntegerField(default=0)
        bathrooms = models.PositiveIntegerField(default=0)

        area = models.PositiveIntegerField(
            help_text="Area in square meters"
        )

        address = models.CharField(max_length=255)
        city = models.CharField(max_length=100)
        state = models.CharField(max_length=100)

        featured = models.BooleanField(default=False)
        is_published = models.BooleanField(default=True)

        realtor = models.ForeignKey(
            "Realtor",
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name="properties",
        )

        created_at = models.DateTimeField(auto_now_add=True)
        updated_at = models.DateTimeField(auto_now=True)
        image = models.ImageField(
                            upload_to="properties/",
                            blank=True,
                            null=True,
                        )

        class Meta:
            ordering = ["-created_at"]

        def __str__(self):
            return self.title

        def get_absolute_url(self):
            return reverse("property-detail", args=[self.slug])


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
    )

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "property"],
                name="unique_user_property_favorite",
            )
        ]

    def __str__(self):
        return f"{self.user.username} saved {self.property.title}"



class Inquiry(models.Model):
    STATUS_CHOICES = [
        ("new", "New"),
        ("contacted", "Contacted"),
        ("closed", "Closed"),
    ]

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="inquiries",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inquiries",
    )

    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)

    message = models.TextField()

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="new",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Inquiry from {self.name} about {self.property.title}"


class Realtor(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="realtor_profile",
    )

    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    agency = models.CharField(max_length=150, blank=True)
    photo = models.ImageField(
        upload_to="realtors/",
        blank=True,
        null=True,
    )

    is_verified = models.BooleanField(default=False)

    applied_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        status = "Verified" if self.is_verified else "Pending"
        return f"{self.user.username} ({status})"
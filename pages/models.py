import random
from datetime import date
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify


MAX_IMAGE_SIZE_MB = 10


def validate_image_file_size(file):
    """Reject uploads over MAX_IMAGE_SIZE_MB before they ever reach
    storage. Without this, an oversized file passes Django's form
    validation, gets accepted, and only fails when the storage
    backend (Cloudinary) tries to upload it — which surfaces as a
    raw, uncaught 500 error instead of a normal form error."""
    max_size_bytes = MAX_IMAGE_SIZE_MB * 1024 * 1024
    if file.size > max_size_bytes:
        raise ValidationError(
            f"Image file too large ({file.size / 1024 / 1024:.1f}MB). "
            f"Maximum size is {MAX_IMAGE_SIZE_MB}MB."
        )

# Create your models here.

class PropertyType(models.Model):
    """Replaces the old hardcoded PROPERTY_TYPES choices list --
    admins can now add/rename property types from Django admin
    without a code deploy."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Location(models.Model):
    """A named area (e.g. "Lekki, Lagos"), distinct from a specific
    property's street address. Multiple properties in the same area
    share one Location, so admins can manage/rename areas in one
    place instead of every property carrying its own free-text
    city/state."""

    name = models.CharField(max_length=150, unique=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="Nigeria")
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        ordering = ["state", "city", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Property(models.Model):
        LISTING_TYPES = [
            ("sale", "For Sale"),
            ("rent", "For Rent"),
        ]

        title = models.CharField(max_length=200)
        slug = models.SlugField(unique=True)

        description = models.TextField()
        amenities = models.TextField(
            blank=True,
            help_text="One amenity per line, e.g. Swimming pool, 24/7 security, Gym",
        )

        property_type = models.ForeignKey(
            PropertyType,
            on_delete=models.PROTECT,
            related_name="properties",
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
        location = models.ForeignKey(
            Location,
            on_delete=models.PROTECT,
            related_name="properties",
        )

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
                            validators=[validate_image_file_size],
                        )

        class Meta:
            ordering = ["-created_at"]
            indexes = [
                # Covers the single most common query shape in the app:
                # "published listings, newest first" — used by the
                # homepage, property list, and favorite/inquiry lookups.
                models.Index(
                    fields=["is_published", "-created_at"],
                    name="property_pub_created_idx",
                ),
                models.Index(
                    fields=["featured", "is_published"],
                    name="property_feat_pub_idx",
                ),
                # No explicit index needed for property_type or
                # location: Django automatically indexes every
                # ForeignKey column, so a custom one here would just
                # duplicate it.
                models.Index(fields=["listing_type"], name="property_listing_type_idx"),
            ]

        def __str__(self):
            return self.title

        def get_absolute_url(self):
            return reverse("property-detail", args=[self.slug])

        @property
        def is_new(self):
            """True if this listing was created within the last 48
            hours, used to show a "New" badge on listing cards."""
            return self.created_at >= timezone.now() - timezone.timedelta(
                hours=48
            )

        @property
        def display_image(self):
            """Which photo represents this listing on cards/grids
            today. With no extra gallery photos, this is just the
            primary image as always. With gallery photos, it rotates
            once per day -- seeded by today's date plus this
            property's id, so every visitor sees the same photo for
            this listing on a given day (no flicker between page
            loads), and it's decided server-side rather than running
            a JS timer on every card in a grid at once."""
            gallery_images = [img.image for img in self.images.all()]
            pool = ([self.image] if self.image else []) + gallery_images

            if not pool:
                return None

            if len(pool) == 1:
                return pool[0]

            seed = f"{date.today().isoformat()}-{self.pk}"
            rng = random.Random(seed)
            return rng.choice(pool)


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

    # Nullable/blank so a guest (not logged in) can still send an inquiry.
    # If they are logged in, the view attaches their account automatically.
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
        indexes = [
            # Realtors filtering their inquiry inbox by status (new /
            # contacted / closed) is the main lookup pattern here.
            models.Index(fields=["status"], name="inquiry_status_idx"),
        ]

    def __str__(self):
        return f"Inquiry from {self.name} about {self.property.title}"

class PropertyImage(models.Model):
    """Extra gallery photos for a listing, beyond its single primary
    Property.image (which stays as the hero/card image, unchanged).
    A realtor can add several of these per listing."""

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(
        upload_to="properties/gallery/",
        validators=[validate_image_file_size],
    )
    caption = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Photo for {self.property.title}"
    

class Realtor(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="realtor_profile",
    )

    # Public profile URL (/realtors/<slug>/). Nullable at the DB
    # level so it's a safe additive migration for existing rows;
    # save() below always fills it in going forward.
    slug = models.SlugField(unique=True, null=True, blank=True)

    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    agency = models.CharField(max_length=150, blank=True)
    photo = models.ImageField(
        upload_to="realtors/",
        blank=True,
        null=True,
        validators=[validate_image_file_size],
    )

    # Approval workflow: users apply, an admin verifies them before
    # they can access the realtor dashboard or create listings.
    is_verified = models.BooleanField(default=False)

    applied_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        status = "Verified" if self.is_verified else "Pending"
        return f"{self.user.username} ({status})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.user.username) or "realtor"
            slug = base_slug
            counter = 1
            while (
                Realtor.objects.filter(slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                counter += 1
                slug = f"{base_slug}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("realtor-detail", args=[self.slug])

    class Meta:
        ordering = ["user__username"]
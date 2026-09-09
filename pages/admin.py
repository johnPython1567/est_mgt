from django.contrib import admin
from django.utils import timezone

# Register your models here.

from .models import Inquiry, Location, Property, PropertyImage, PropertyType, Realtor, Review, ListingReport


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


@admin.action(description="Mark selected listings as verified")
def mark_properties_verified(modeladmin, request, queryset):
    updated = queryset.filter(is_verified=False).update(
        is_verified=True, verified_at=timezone.now()
    )
    modeladmin.message_user(request, f"{updated} listing(s) marked verified.")


@admin.action(description="Remove verification from selected listings")
def mark_properties_unverified(modeladmin, request, queryset):
    updated = queryset.filter(is_verified=True).update(
        is_verified=False, verified_at=None
    )
    modeladmin.message_user(
        request, f"Verification removed from {updated} listing(s)."
    )


@admin.action(description="Mark selected listings as featured")
def mark_properties_featured(modeladmin, request, queryset):
    updated = queryset.filter(featured=False).update(featured=True)
    modeladmin.message_user(request, f"{updated} listing(s) marked featured.")


@admin.action(description="Remove selected listings from featured")
def mark_properties_not_featured(modeladmin, request, queryset):
    updated = queryset.filter(featured=True).update(featured=False)
    modeladmin.message_user(
        request, f"{updated} listing(s) removed from featured."
    )


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    inlines = [PropertyImageInline]

    list_display = (
        "title",
        "property_type",
        "listing_type",
        "price",
        "location",
        "realtor",
        "featured",
        "is_verified",
        "is_published",
        "created_at",
    )

    list_select_related = ("realtor", "realtor__user", "property_type", "location")

    list_filter = (
        "property_type",
        "listing_type",
        "featured",
        "is_verified",
        "is_published",
    )

    search_fields = (
        "title",
        "description",
        "location__city",
        "location__state",
    )

    autocomplete_fields = ("property_type", "location")

    prepopulated_fields = {
        "slug": ("title",)
    }

    actions = [
        mark_properties_verified,
        mark_properties_unverified,
        mark_properties_featured,
        mark_properties_not_featured,
    ]


@admin.register(PropertyType)
class PropertyTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "state", "country")
    list_filter = ("state", "country")
    search_fields = ("name", "city", "state")
    prepopulated_fields = {"slug": ("name",)}



@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_select_related = ("property", "user")

    list_display = (
        "name",
        "email",
        "property",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "name",
        "email",
        "phone",
        "message",
        "property__title",
    )

    autocomplete_fields = ("property",)



@admin.action(description="Approve selected realtor applications")
def approve_realtors(modeladmin, request, queryset):
    updated = queryset.filter(is_verified=False).update(
        is_verified=True,
        verified_at=timezone.now(),
    )
    modeladmin.message_user(request, f"{updated} realtor(s) approved.")


@admin.register(Realtor)
class RealtorAdmin(admin.ModelAdmin):
    list_select_related = ("user",)

    list_display = (
        "user",
        "agency",
        "phone",
        "is_verified",
        "average_rating",
        "review_count",
        "applied_at",
    )

    list_filter = ("is_verified",)

    search_fields = (
        "user__username",
        "user__email",
        "agency",
        "phone",
    )

    actions = [approve_realtors]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_select_related = ("realtor", "realtor__user", "user")

    list_display = (
        "realtor",
        "user",
        "rating",
        "created_at",
    )

    list_filter = ("rating",)

    search_fields = (
        "realtor__user__username",
        "user__username",
        "comment",
    )


@admin.action(description="Mark selected reports as reviewed")
def mark_reviewed(modeladmin, request, queryset):
    updated = queryset.update(status="reviewed")
    modeladmin.message_user(request, f"{updated} report(s) marked reviewed.")


@admin.action(description="Dismiss selected reports")
def mark_dismissed(modeladmin, request, queryset):
    updated = queryset.update(status="dismissed")
    modeladmin.message_user(request, f"{updated} report(s) dismissed.")


@admin.register(ListingReport)
class ListingReportAdmin(admin.ModelAdmin):
    list_select_related = ("property",)

    list_display = (
        "property",
        "reason",
        "reporter_name",
        "status",
        "created_at",
    )

    list_filter = ("reason", "status")

    search_fields = (
        "property__title",
        "reporter_name",
        "reporter_email",
        "details",
    )

    actions = [mark_reviewed, mark_dismissed]
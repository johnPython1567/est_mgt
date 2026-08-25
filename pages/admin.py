from django.contrib import admin
from django.utils import timezone

# Register your models here.

from .models import Inquiry, Location, Property, PropertyImage, PropertyType, Realtor

class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


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
        "is_published",
        "created_at",
    )

    list_select_related = ("realtor", "realtor__user", "property_type", "location")

    list_filter = (
        "property_type",
        "listing_type",
        "featured",
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
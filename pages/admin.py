from django.contrib import admin
from .models import Inquiry, Property, Realtor

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "property_type",
        "listing_type",
        "price",
        "city",
        "realtor",
        "featured",
        "is_published",
        "created_at",
    )

    list_filter = (
        "property_type",
        "listing_type",
        "featured",
        "is_published",
    )

    search_fields = (
        "title",
        "description",
        "city",
        "state",
    )

    prepopulated_fields = {
        "slug": ("title",)
    }


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
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
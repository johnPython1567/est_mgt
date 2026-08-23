from django.contrib import admin
from .models import Inquiry, Property

# Register your models here.
from django.contrib import admin
from .models import Property


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "property_type",
        "listing_type",
        "price",
        "city",
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
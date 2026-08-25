from django.db import migrations
from django.utils.text import slugify


# The exact canonical choices that used to live on Property.PROPERTY_TYPES,
# reproduced here so this migration has no runtime dependency on the
# current models.py (migrations must stay self-contained -- models.py
# will keep changing long after this file is written).
PROPERTY_TYPE_CHOICES = [
    ("house", "House"),
    ("apartment", "Apartment"),
    ("condo", "Condo"),
    ("townhouse", "Townhouse"),
    ("land", "Land"),
    ("commercial", "Commercial"),
    ("office", "Office"),
    ("warehouse", "Warehouse"),
]


def unique_slug(model, base_slug):
    base_slug = base_slug or "item"
    slug = base_slug
    counter = 1
    while model.objects.filter(slug=slug).exists():
        counter += 1
        slug = f"{base_slug}-{counter}"
    return slug


def backfill(apps, schema_editor):
    Property = apps.get_model('pages', 'Property')
    PropertyType = apps.get_model('pages', 'PropertyType')
    Location = apps.get_model('pages', 'Location')

    # Seed PropertyType from the known canonical choices first, so
    # display names match exactly what users have seen all along
    # rather than being derived/guessed from raw stored values.
    type_lookup = {}
    for value, label in PROPERTY_TYPE_CHOICES:
        obj, _ = PropertyType.objects.get_or_create(
            name=label,
            defaults={"slug": unique_slug(PropertyType, slugify(label))},
        )
        type_lookup[value] = obj

    location_lookup = {}

    # Explicit ascending-by-pk order (not Property's default
    # descending -created_at) so which row's exact casing "wins" as
    # the canonical Location name is deterministic and predictable,
    # rather than depending on insertion order by accident.
    for prop in Property.objects.all().order_by("pk"):
        # property_type: map the old CharField value to its matching
        # PropertyType, creating one defensively if some unexpected
        # value slipped in outside the known choices (belt and
        # suspenders -- shouldn't happen given the field had a fixed
        # choices list, but a migration must never crash on a live
        # database over a value it didn't anticipate).
        old_value = prop.property_type
        if old_value not in type_lookup:
            label = old_value.title() if old_value else "Other"
            obj, _ = PropertyType.objects.get_or_create(
                name=label,
                defaults={"slug": unique_slug(PropertyType, slugify(label))},
            )
            type_lookup[old_value] = obj
        prop.property_type_fk_id = type_lookup[old_value].id

        # location: one Location row per distinct (city, state) pair.
        # Normalize to title case so "lagos"/"Lagos"/"LAGOS" all
        # resolve to one clean "Lagos" row instead of three untidy
        # variants -- matches the same normalization PropertyForm
        # applies going forward for newly created properties.
        city = (prop.city or "").strip().title()
        state = (prop.state or "").strip().title()
        key = (city.lower(), state.lower())

        if key not in location_lookup:
            # Also check the database directly (case-insensitively),
            # not just this migration run's in-memory cache, in case
            # a matching Location already exists from elsewhere.
            existing = Location.objects.filter(
                city__iexact=city, state__iexact=state
            ).first()

            if existing is not None:
                location_lookup[key] = existing
            else:
                if city and state:
                    name = f"{city}, {state}"
                else:
                    name = city or state or "Unspecified"

                loc = Location.objects.create(
                    city=city,
                    state=state,
                    name=name,
                    slug=unique_slug(Location, slugify(name)),
                )
                location_lookup[key] = loc

        prop.location_id = location_lookup[key].id

        prop.save(update_fields=["property_type_fk", "location"])


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0008_propertytype_location'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
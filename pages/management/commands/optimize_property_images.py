from pathlib import Path, PurePosixPath

from PIL import Image, ImageOps
from django.conf import settings
from django.core.management.base import BaseCommand

from pages.models import Property


class Command(BaseCommand):
    help = "Create optimized WebP property images. Originals are preserved."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write WebP files and update property image references.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        max_dimension = 1920
        processed = 0

        for property_obj in Property.objects.exclude(image=""):
            source_name = property_obj.image.name

            if source_name.lower().endswith(".webp"):
                self.stdout.write(f"Skipping {source_name}; already WebP.")
                continue

            source_path = Path(settings.MEDIA_ROOT) / source_name
            if not source_path.exists():
                self.stderr.write(f"Missing file: {source_name}")
                continue

            output_name = str(PurePosixPath(source_name).with_suffix(".webp"))
            output_path = Path(settings.MEDIA_ROOT) / output_name

            with Image.open(source_path) as image:
                image = ImageOps.exif_transpose(image)
                image.thumbnail(
                    (max_dimension, max_dimension),
                    Image.Resampling.LANCZOS,
                )

                if image.mode not in ("RGB", "L"):
                    image = image.convert("RGB")

                if apply_changes:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    image.save(output_path, "WEBP", quality=82, method=6)
                    property_obj.image.name = output_name
                    property_obj.save(update_fields=["image"])

            action = "Optimized" if apply_changes else "Would optimize"
            self.stdout.write(f"{action}: {source_name} -> {output_name}")

        self.stdout.write(self.style.SUCCESS(f"Processed {processed} image(s)."))
        processed += 1
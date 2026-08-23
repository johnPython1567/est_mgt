import json
from pathlib import Path

from django import template
from django.conf import settings


register = template.Library()


MANIFEST_PATH = (
    settings.BASE_DIR
    / "static"
    / "dist"
    / ".vite"
    / "manifest.json"
)


def get_manifest():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


@register.simple_tag
def vite_css():
    manifest = get_manifest()

    css_file = manifest["src/css/input.css"]["file"]

    return f"/static/dist/{css_file}"


@register.simple_tag
def vite_js():
    manifest = get_manifest()

    js_file = manifest["src/js/main.js"]["file"]

    return f"/static/dist/{js_file}"
from urllib.parse import quote

from django import template

register = template.Library()


@register.filter
def whatsapp_with_message(realtor, message):
    """Usage: {{ realtor|whatsapp_with_message:"Hi, I'm interested..." }}

    Builds on Realtor.whatsapp_url (which handles phone number
    normalization) by adding a pre-filled message to the chat.
    Returns an empty string -- not None -- when the realtor has no
    usable phone number, so it's always safe to drop directly into
    an href without an extra {% if %} check in the template.
    """
    base_url = realtor.whatsapp_url
    if not base_url:
        return ""
    return f"{base_url}?text={quote(message)}"
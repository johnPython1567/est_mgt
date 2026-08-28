def compare_properties(request):
    """Makes compare_count available to every template (e.g. for a
    nav-wide "Compare (2)" indicator) without every single view
    needing to add it to its own context manually."""
    compare_ids = request.session.get("compare_property_ids", [])
    return {
        "compare_count": len(compare_ids),
    }

def pending_realtor_applications(request):
    """Makes pending_realtor_count available to every template, so
    staff see a nav-wide notification for realtor applications
    awaiting approval -- without needing to remember to check
    /admin/ periodically. Only computed for staff, so this adds no
    extra query for ordinary visitors."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return {}

    from .models import Realtor

    return {
        "pending_realtor_count": Realtor.objects.filter(
            is_verified=False
        ).count()
    }

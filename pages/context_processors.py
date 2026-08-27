def compare_properties(request):
    """Makes compare_count available to every template (e.g. for a
    nav-wide "Compare (2)" indicator) without every single view
    needing to add it to its own context manually."""
    compare_ids = request.session.get("compare_property_ids", [])
    return {
        "compare_count": len(compare_ids),
    }



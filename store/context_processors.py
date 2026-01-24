from .models import Category, SiteSettings, NavLink
from .cart import cart_items_with_totals

def nav_categories(request):
    parents = Category.objects.filter(
        is_active=True,
        parent__isnull=True
    ).prefetch_related("children")

    return {
        "nav_parents": parents
    }
def cart_context(request):
    items, total = cart_items_with_totals(request)
    count = sum(i["qty"] for i in items)
    return {
        "cart_count": count,
        "cart_total": total,
    }

def site_settings(request):
    settings_obj = SiteSettings.objects.first()
    return {
        "site_settings": settings_obj,
        "nav_links_header": NavLink.objects.filter(is_active=True, location="header").order_by("sort_order", "label"),
        "nav_links_footer": NavLink.objects.filter(is_active=True, location="footer").order_by("sort_order", "label"),
        "nav_links_mobile": NavLink.objects.filter(is_active=True, location="mobile").order_by("sort_order", "label"),
    }

from .models import Category
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

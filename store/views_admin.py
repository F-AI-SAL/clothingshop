from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count
from django.urls import reverse
from django.utils import timezone
from django.shortcuts import render

from .models import Order, OrderItem

@staff_member_required
def admin_dashboard(request):
    now = timezone.now()
    start_7d = now - timedelta(days=7)
    start_30d = now - timedelta(days=30)

    revenue_7d = Order.objects.filter(created_at__gte=start_7d).aggregate(s=Sum("total"))["s"] or 0
    revenue_30d = Order.objects.filter(created_at__gte=start_30d).aggregate(s=Sum("total"))["s"] or 0

    orders_7d = Order.objects.filter(created_at__gte=start_7d).count()
    orders_30d = Order.objects.filter(created_at__gte=start_30d).count()

    by_status = Order.objects.values("status").annotate(c=Count("id")).order_by("-c")

    top_products = (
        OrderItem.objects.values("product__title")
        .annotate(q=Sum("qty"), amount=Sum("line_total"))
        .order_by("-q")[:10]
    )

    recent_orders = Order.objects.order_by("-created_at")[:6]
    pending_orders = Order.objects.filter(status="pending").count()
    admin_orders_url = reverse("admin:store_order_changelist")

    return render(request, "store/admin_dashboard.html", {
        "revenue_7d": revenue_7d,
        "revenue_30d": revenue_30d,
        "orders_7d": orders_7d,
        "orders_30d": orders_30d,
        "by_status": by_status,
        "top_products": top_products,
        "recent_orders": recent_orders,
        "pending_orders": pending_orders,
        "admin_orders_url": admin_orders_url,
    })

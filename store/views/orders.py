from django.shortcuts import render, get_object_or_404

from ..models import Order


def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "store/order_success.html", {"order": order})

from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from ..cart import (
    cart_add_item,
    cart_remove_item,
    cart_items_with_totals,
    cart_set_item,
)
from ..models import Product, ProductVariant


# -----------------------
# CART
# -----------------------
def cart_detail(request):
    items, total = cart_items_with_totals(request)
    return render(request, "store/cart_detail.html", {
        "items": items,
        "total": total,
    })


def cart_add(request, product_id):
    if request.method != "POST":
        return redirect("store:product_list")

    product = get_object_or_404(Product, id=product_id, is_active=True)

    qty = int(request.POST.get("qty", 1))
    color = (request.POST.get("color") or "").strip()
    size = (request.POST.get("size") or "").strip()

    referer = request.META.get("HTTP_REFERER")
    product_url = reverse("store:product_detail", args=[product.slug])
    fallback_url = referer or product_url
    success_url = referer or reverse("store:cart_detail")

    variant_qs = ProductVariant.objects.filter(product=product, is_active=True)

    if variant_qs.exists():
        if not color or not size:
            messages.error(request, "Please select a valid color & size.")
            return redirect(fallback_url)

        variant = variant_qs.filter(color=color, size=size).first()
        if not variant:
            messages.error(request, "Please select a valid color & size.")
            return redirect(fallback_url)

        if qty > variant.stock_qty:
            messages.error(request, f"Only {variant.stock_qty} left in stock.")
            return redirect(fallback_url)

    cart_add_item(
        request,
        product_id=product.id,
        qty=qty,
        color=color,
        size=size
    )

    messages.success(request, "Added to cart ?")
    return redirect(success_url)


def cart_update(request, product_id):
    if request.method != "POST":
        return redirect("store:cart_detail")

    qty = request.POST.get("qty", 1)
    cart_set_item(request, product_id=product_id, qty=qty)

    messages.success(request, "Cart updated ?")
    return redirect("store:cart_detail")


def cart_remove(request, product_id):
    cart_remove_item(request, product_id)
    messages.success(request, "Removed from cart ?")
    return redirect("store:cart_detail")

from .coupons import validate_coupon, calc_discount
from django.db.models import F

from decimal import Decimal

from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from .emails import send_order_created_notifications

from .models import (
    Category,
    HomeBanner,
    FeaturedBanner,
    Product,
    Order,
    OrderItem,
    ProductVariant,
    Coupon,
)

from .cart import (
    cart_add_item,
    cart_remove_item,
    cart_items_with_totals,
    cart_set_item,
    clear_cart,
)


# -----------------------
# HOME
# -----------------------
def home(request):
    banner = HomeBanner.objects.filter(is_active=True).first()

    # ✅ multiple featured (slider)
    now = timezone.now()
    featured_banners = FeaturedBanner.objects.filter(
        is_active=True
    ).order_by("sort_order", "-created_at")

    products = Product.objects.filter(is_active=True).order_by("-created_at")[:8]

    return render(request, "store/home.html", {
        "banner": banner,
        "featured_banners": featured_banners,   # if you use slider section
        "products": products,
    })


# -----------------------
# PRODUCT LIST
# -----------------------
def product_list(request):
    products = Product.objects.filter(is_active=True).order_by("-created_at")

    cat_slug = request.GET.get("cat")
    if cat_slug:
        products = products.filter(category__slug=cat_slug)

    return render(request, "store/product_list.html", {
        "products": products,
    })


# -----------------------
# PRODUCT DETAIL
# -----------------------
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    images = product.images.all()

    related = Product.objects.filter(
        is_active=True,
        category=product.category
    ).exclude(id=product.id).order_by("-created_at")[:4]

    return render(request, "store/product_detail.html", {
        "product": product,
        "images": images,
        "related": related,
    })


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

    messages.success(request, "Added to cart ✅")
    return redirect(success_url)


def cart_update(request, product_id):
    if request.method != "POST":
        return redirect("store:cart_detail")

    qty = request.POST.get("qty", 1)
    cart_set_item(request, product_id=product_id, qty=qty)

    messages.success(request, "Cart updated ✅")
    return redirect("store:cart_detail")


def cart_remove(request, product_id):
    cart_remove_item(request, product_id)
    messages.success(request, "Removed from cart ✅")
    return redirect("store:cart_detail")

# -----------------------
# CHECKOUT + ORDER CREATE
# -----------------------
def checkout(request):
    items, subtotal = cart_items_with_totals(request)

    if not items:
        messages.error(request, "Your cart is empty.")
        return redirect("store:product_list")

    coupon_code = (request.session.get("coupon_code") or "").strip().upper()
    coupon_obj = None
    discount = Decimal("0.00")

    if coupon_code:
        coupon_obj, err = validate_coupon(coupon_code, subtotal)
        if coupon_obj:
            discount = calc_discount(coupon_obj, subtotal)
        else:
            request.session["coupon_code"] = ""
            request.session.modified = True
            messages.error(request, err)

    # ✅ later: dynamic shipping & coupons
    shipping_cost = Decimal("0.00")
    total = subtotal - discount + shipping_cost

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()

        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        area = request.POST.get("area", "").strip()
        postal_code = request.POST.get("postal_code", "").strip()

        payment_method = request.POST.get("payment_method", "cod")
        notes = request.POST.get("notes", "").strip()

        if not full_name or not phone or not address:
            messages.error(request, "Please fill Full name, Phone and Address.")
            return redirect("store:checkout")

        # ✅ Create order
        order = Order.objects.create(
            full_name=full_name,
            phone=phone,
            email=email,

            address=address,
            city=city,
            area=area,
            postal_code=postal_code,

            payment_method=payment_method,
            notes=notes,

            subtotal=subtotal,
            discount=discount,
            shipping_cost=shipping_cost,
            total=total,
            status="pending",
        )

        # ✅ Create items
        for it in items:
            p = it["product"]
            OrderItem.objects.create(
                order=order,
                product=p,
                qty=it["qty"],
                price=p.price,
                color=it.get("color") or "",
                size=it.get("size") or "",
            )

        if coupon_obj:
            Coupon.objects.filter(id=coupon_obj.id).update(used_count=F("used_count") + 1)
            request.session["coupon_code"] = ""
            request.session.modified = True

        clear_cart(request)
        messages.success(request, "Order placed successfully ✅")
        send_order_created_notifications(order)
        return redirect("store:order_success", order_id=order.id)

    return render(request, "store/checkout.html", {
        "items": items,
        "subtotal": subtotal,
        "discount": discount,
        "shipping_cost": shipping_cost,
        "total": total,
    })

def apply_coupon(request):
    if request.method != "POST":
        return redirect("store:checkout")

    code = (request.POST.get("coupon") or "").strip().upper()
    request.session["coupon_code"] = code
    request.session.modified = True
    messages.success(request, "Coupon applied ✅")
    return redirect("store:checkout")

def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "store/order_success.html", {"order": order})

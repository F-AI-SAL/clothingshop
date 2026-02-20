import logging
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect

from ..cart import cart_items_with_totals, clear_cart
from ..coupons import validate_coupon, calc_discount
from ..emails import send_order_created_notifications
from ..notifications.dispatch import send_sms, send_whatsapp
from ..services.orders import create_order_from_cart


logger = logging.getLogger(__name__)

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

    # later: dynamic shipping & coupons
    shipping_cost = Decimal("0.00")

    vat_rate = settings.VAT_RATE
    vat_amount = (subtotal - discount) * Decimal(str(vat_rate)) / Decimal("100")
    cod_charge = Decimal("0.00")

    total = subtotal - discount + shipping_cost + vat_amount + cod_charge

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()

        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        area = request.POST.get("area", "").strip()
        postal_code = request.POST.get("postal_code", "").strip()

        payment_method = request.POST.get("payment_method", "cod")
        cod_charge = Decimal(str(settings.COD_CHARGE)) if payment_method == "cod" else Decimal("0.00")
        cod_confirmed = False if (payment_method == "cod" and settings.COD_CONFIRMATION_REQUIRED) else True
        payment_reference = (request.POST.get("payment_reference") or "").strip()
        payment_proof = request.FILES.get("payment_proof")
        notes = request.POST.get("notes", "").strip()

        total = subtotal - discount + shipping_cost + vat_amount + cod_charge

        if not full_name or not phone or not address:
            messages.error(request, "Please fill Full name, Phone and Address.")
            return redirect("store:checkout")
        if payment_method in ("bkash", "nagad", "bank"):
            if not payment_reference or not payment_proof:
                messages.error(request, "Please add transaction ID and payment screenshot.")
                return redirect("store:checkout")

        try:
            order = create_order_from_cart(
                vat_rate=vat_rate,
                vat_amount=vat_amount,
                cod_charge=cod_charge,
                cod_confirmed=cod_confirmed,
                items=items,
                subtotal=subtotal,
                discount=discount,
                shipping_cost=shipping_cost,
                total=total,
                coupon_obj=coupon_obj,
                full_name=full_name,
                phone=phone,
                email=email,
                address=address,
                city=city,
                area=area,
                postal_code=postal_code,
                payment_method=payment_method,
                payment_reference=payment_reference,
                payment_proof=payment_proof,
                notes=notes,
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("store:checkout")

        if coupon_obj:
            request.session["coupon_code"] = ""
            request.session.modified = True

        clear_cart(request)
        messages.success(request, "Order placed successfully OK")

        def _send_order_created():
            try:
                send_order_created_notifications(order)
                send_sms(order, "Your order has been placed.")
                send_whatsapp(order, "order_placed", {"order_id": order.id})
            except Exception:
                logger.exception("Failed to send order created notifications for order %s", order.id)

        transaction.on_commit(_send_order_created)
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
    messages.success(request, "Coupon applied OK")
    return redirect("store:checkout")

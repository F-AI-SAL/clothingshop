from django.db import transaction
from django.db.models import F

from ..models import Order, OrderItem, PaymentTransaction, ProductVariant, Coupon


def _lock_and_validate_stock(items):
    variant_keys = []
    for it in items:
        product = it["product"]
        qty = it["qty"]
        color = (it.get("color") or "").strip()
        size = (it.get("size") or "").strip()

        variant_qs = ProductVariant.objects.filter(product=product, is_active=True)
        if not variant_qs.exists():
            continue

        if not color or not size:
            raise ValueError("Please select a valid color & size.")

        variant = variant_qs.filter(color=color, size=size).first()
        if not variant:
            raise ValueError("Please select a valid color & size.")

        if qty > variant.stock_qty:
            raise ValueError(f"Only {variant.stock_qty} left in stock.")

        variant_keys.append((variant.id, qty))

    return variant_keys


def create_order_from_cart(*, items, subtotal, discount, shipping_cost, total, coupon_obj,
                           vat_rate=0, vat_amount=0, cod_charge=0, cod_confirmed=False,
                           full_name, phone, email, address, city, area, postal_code,
                           payment_method, payment_reference, payment_proof, notes):
    with transaction.atomic():
        variant_keys = _lock_and_validate_stock(items)

        if variant_keys:
            ids = [vid for vid, _ in variant_keys]
            locked = {v.id: v for v in ProductVariant.objects.select_for_update().filter(id__in=ids)}
            for vid, qty in variant_keys:
                variant = locked.get(vid)
                if not variant:
                    raise ValueError("Please select a valid color & size.")
                if qty > variant.stock_qty:
                    raise ValueError(f"Only {variant.stock_qty} left in stock.")
                variant.stock_qty = max(0, variant.stock_qty - qty)
                variant.save(update_fields=["stock_qty"])

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
            vat_rate=vat_rate,
            vat_amount=vat_amount,
            cod_charge=cod_charge,
            cod_confirmed=cod_confirmed,
            total=total,
            status="pending",
        )

        for it in items:
            product = it["product"]
            OrderItem.objects.create(
                order=order,
                product=product,
                qty=it["qty"],
                price=product.price,
                color=it.get("color") or "",
                size=it.get("size") or "",
            )

        PaymentTransaction.objects.create(
            order=order,
            method=payment_method,
            amount=total,
            reference_id=payment_reference,
            proof_image=payment_proof,
        )

        if coupon_obj:
            Coupon.objects.filter(id=coupon_obj.id).update(used_count=F("used_count") + 1)

        return order

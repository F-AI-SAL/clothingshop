from django.utils import timezone
from decimal import Decimal
from .models import Coupon

def validate_coupon(code: str, subtotal: Decimal):
    code = (code or "").strip().upper()
    if not code:
        return None, "Enter a coupon code."

    c = Coupon.objects.filter(code=code, is_active=True).first()
    if not c:
        return None, "Invalid coupon."

    now = timezone.now()
    if c.start_at and now < c.start_at:
        return None, "Coupon not started yet."
    if c.end_at and now > c.end_at:
        return None, "Coupon expired."
    if subtotal < c.min_subtotal:
        return None, f"Minimum order PKR {c.min_subtotal} required."
    if c.max_uses and c.used_count >= c.max_uses:
        return None, "Coupon limit reached."

    return c, None

def calc_discount(coupon: Coupon, subtotal: Decimal) -> Decimal:
    if coupon.discount_type == "percent":
        return (subtotal * coupon.value / Decimal("100")).quantize(Decimal("0.01"))
    return min(subtotal, coupon.value)
from decimal import Decimal
from .models import Product

CART_SESSION_ID = "cart"

def get_cart(request):
    return request.session.get(CART_SESSION_ID, {})

def save_cart(request, cart):
    request.session[CART_SESSION_ID] = cart
    request.session.modified = True

def cart_add_item(request, product_id, qty=1, color=None, size=None):
    cart = get_cart(request)
    key = str(product_id)

    item = cart.get(key, {"qty": 0, "color": color, "size": size})
    item["qty"] = int(item["qty"]) + int(qty)

    # keep last selected variant
    item["color"] = color or item.get("color")
    item["size"] = size or item.get("size")

    cart[key] = item
    save_cart(request, cart)

def cart_remove_item(request, product_id):
    cart = get_cart(request)
    key = str(product_id)
    if key in cart:
        del cart[key]
        save_cart(request, cart)

def cart_items_with_totals(request):
    cart = get_cart(request)
    product_ids = [int(pid) for pid in cart.keys()] if cart else []
    products = Product.objects.filter(id__in=product_ids, is_active=True)

    items = []
    total = Decimal("0.00")

    prod_map = {p.id: p for p in products}
    for pid_str, data in cart.items():
        pid = int(pid_str)
        product = prod_map.get(pid)
        if not product:
            continue
        qty = int(data.get("qty", 1))
        line_total = product.price * qty
        total += line_total
        items.append({
            "product": product,
            "qty": qty,
            "color": data.get("color"),
            "size": data.get("size"),
            "line_total": line_total
        })

    return items, total
def cart_set_item(request, product_id, qty, color=None, size=None):
    """
    Set exact qty for an item. If qty <= 0 remove it.
    """
    cart = get_cart(request)
    key = str(product_id)
    qty = int(qty)

    if qty <= 0:
        if key in cart:
            del cart[key]
            save_cart(request, cart)
        return

    item = cart.get(key, {"qty": 0, "color": color, "size": size})
    item["qty"] = qty
    item["color"] = color or item.get("color")
    item["size"] = size or item.get("size")

    cart[key] = item
    save_cart(request, cart)


def clear_cart(request):
    save_cart(request, {})
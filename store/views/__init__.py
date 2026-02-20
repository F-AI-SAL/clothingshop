from .home import home
from .catalog import product_list, product_detail
from .cart import cart_detail, cart_add, cart_update, cart_remove
from .checkout import checkout, apply_coupon
from .orders import order_success

__all__ = [
    "home",
    "product_list",
    "product_detail",
    "cart_detail",
    "cart_add",
    "cart_update",
    "cart_remove",
    "checkout",
    "apply_coupon",
    "order_success",
]

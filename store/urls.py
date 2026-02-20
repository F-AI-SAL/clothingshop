from django.urls import path
from . import views
from .views import payment_webhooks

app_name = "store"

urlpatterns = [
    # Pages
    path("", views.home, name="home"),
    path("products/", views.product_list, name="product_list"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),

    # Cart
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),

    # Checkout / Order
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/coupon/", views.apply_coupon, name="apply_coupon"),
    path("order/success/<int:order_id>/", views.order_success, name="order_success"),
    # Webhooks
    path("webhooks/bkash/", payment_webhooks.bkash_webhook, name="bkash_webhook"),
    path("webhooks/nagad/", payment_webhooks.nagad_webhook, name="nagad_webhook"),
    path("webhooks/bank/", payment_webhooks.bank_webhook, name="bank_webhook"),

]
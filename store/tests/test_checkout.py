from django.test import TestCase, override_settings
from django.urls import reverse

from store.cart import CART_SESSION_ID
from store.models import Category, Product, Order, OrderItem, PaymentTransaction


@override_settings(SECURE_SSL_REDIRECT=False)
class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Suits")
        self.product = Product.objects.create(
            category=self.category,
            title="Navy Suit",
            price="120.00",
            is_active=True,
        )

    def test_checkout_creates_order(self):
        session = self.client.session
        session[CART_SESSION_ID] = {str(self.product.id): {"qty": 2, "color": "", "size": ""}}
        session.save()

        checkout_url = reverse("store:checkout")
        response = self.client.post(checkout_url, {
            "full_name": "Test Customer",
            "phone": "01700000000",
            "email": "test@example.com",
            "address": "Dhaka",
            "city": "Dhaka",
            "area": "Banani",
            "postal_code": "1213",
            "payment_method": "cod",
            "notes": "Please call",
        })

        self.assertIn(response.status_code, (301, 302))
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)
        self.assertEqual(PaymentTransaction.objects.count(), 1)

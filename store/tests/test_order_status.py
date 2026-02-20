from unittest.mock import patch

from django.test import TestCase

from store.models import Order


class OrderStatusSignalTests(TestCase):
    def test_status_change_sends_notification(self):
        order = Order.objects.create(
            full_name="Test Customer",
            phone="01700000000",
            email="test@example.com",
            address="Dhaka",
            city="Dhaka",
            area="Banani",
            postal_code="1213",
            payment_method="cod",
            notes="",
            subtotal="100.00",
            discount="0.00",
            shipping_cost="0.00",
            total="100.00",
            status="pending",
        )

        with patch("store.emails.send_status_update_notification") as mocked:
            order.status = "processing"
            with self.captureOnCommitCallbacks(execute=True):
                order.save()
            mocked.assert_called_once()

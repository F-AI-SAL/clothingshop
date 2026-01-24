from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from store.models import Order


class Command(BaseCommand):
    help = "Anonymize orders older than N days for GDPR-like compliance."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=365, help="Anonymize orders older than this many days.")

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        qs = Order.objects.filter(created_at__lt=cutoff)
        updated = 0
        for order in qs.iterator():
            order.full_name = "Anonymized"
            order.phone = ""
            order.email = ""
            order.address = ""
            order.city = ""
            order.area = ""
            order.postal_code = ""
            order.notes = ""
            order.save(
                update_fields=[
                    "full_name",
                    "phone",
                    "email",
                    "address",
                    "city",
                    "area",
                    "postal_code",
                    "notes",
                ]
            )
            if hasattr(order, "payment") and order.payment.proof_image:
                order.payment.proof_image.delete(save=True)
            updated += 1
        self.stdout.write(self.style.SUCCESS(f"Anonymized {updated} order(s)."))

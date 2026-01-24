import json
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand

from store.models import Order, OrderItem


class Command(BaseCommand):
    help = "Export GDPR data for a given email to a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Customer email to export")
        parser.add_argument("--output-dir", default="gdpr_exports", help="Output directory")

    def handle(self, *args, **options):
        email = options["email"]
        orders = Order.objects.filter(email=email).prefetch_related("items")
        payload = []
        for order in orders:
            payload.append({
                "order_id": order.id,
                "full_name": order.full_name,
                "phone": order.phone,
                "email": order.email,
                "address": order.address,
                "city": order.city,
                "area": order.area,
                "postal_code": order.postal_code,
                "status": order.status,
                "total": str(order.total),
                "created_at": order.created_at.isoformat(),
                "items": [
                    {
                        "product": item.product.title,
                        "qty": item.qty,
                        "price": str(item.price),
                        "color": item.color,
                        "size": item.size,
                    }
                    for item in order.items.all()
                ],
            })

        out_dir = Path(options["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = out_dir / f"gdpr_export_{email}_{timestamp}.json"
        out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"GDPR export written to {out_file}"))

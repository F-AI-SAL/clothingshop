from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.core.files.base import ContentFile

from store.models import Category, Product, ProductVariant, ProductImage


COLOR_MAP = {
    "Navy": "#0f172a",
    "Black": "#111111",
    "Charcoal": "#374151",
    "Emerald": "#047857",
    "Rose": "#f43f5e",
    "Beige": "#e7d8c9",
    "Red": "#b91c1c",
    "Gold": "#ca8a04",
    "Maroon": "#7f1d1d",
    "White": "#f8fafc",
}



def _make_image(color_hex):
    try:
        from PIL import Image
    except Exception:
        return None

    color = color_hex or "#cccccc"
    img = Image.new("RGB", (600, 800), color)
    buf = ContentFile(b"")
    from io import BytesIO
    tmp = BytesIO()
    img.save(tmp, format="JPEG", quality=85)
    buf.write(tmp.getvalue())
    return buf

class Command(BaseCommand):
    help = "Seed demo categories/products/variants for showcase"

    def handle(self, *args, **options):
        categories = [
            ("Men's Formal", None),
            ("Women's Formal", None),
            ("Couple", None),
        ]

        cat_map = {}
        for name, parent in categories:
            obj, _ = Category.objects.get_or_create(name=name, defaults={"slug": slugify(name)})
            cat_map[name] = obj

        products = [
            ("Men's Formal", "Navy Suit", 120.00, ["Navy", "Black"], ["S", "M", "L", "XL"]),
            ("Men's Formal", "Charcoal Blazer", 95.00, ["Charcoal", "Black"], ["S", "M", "L", "XL"]),
            ("Men's Formal", "Classic Tuxedo", 180.00, ["Black"], ["M", "L", "XL"]),
            ("Women's Formal", "Emerald Gown", 150.00, ["Emerald", "Black"], ["S", "M", "L"]),
            ("Women's Formal", "Rose Maxi Dress", 110.00, ["Rose", "Beige"], ["S", "M", "L"]),
            ("Women's Formal", "Satin Saree", 90.00, ["Red", "Gold"], ["Free"]),
            ("Couple", "Royal Couple Set", 220.00, ["Navy", "Maroon"], ["S", "M", "L", "XL"]),
            ("Couple", "Classic Couple Set", 200.00, ["Black", "White"], ["S", "M", "L", "XL"]),
            ("Couple", "Golden Couple Set", 240.00, ["Gold"], ["M", "L"]),
        ]

        created = 0
        for cat_name, title, price, colors, sizes in products:
            cat = cat_map[cat_name]
            product, is_new = Product.objects.get_or_create(
                category=cat,
                title=title,
                defaults={
                    "slug": slugify(title),
                    "price": price,
                    "colors": ", ".join(colors),
                    "sizes": ", ".join(sizes),
                    "is_active": True,
                },
            )
            if is_new:
                created += 1

            for color in colors:
                for size in sizes:
                    ProductVariant.objects.get_or_create(
                        product=product,
                        color=color,
                        size=size,
                        defaults={"stock_qty": 10, "is_active": True},
                    )

            # add generated local image if none
            if not product.images.exists():
                color_hex = COLOR_MAP.get(colors[0], "#cccccc")
                image_file = _make_image(color_hex)
                if image_file:
                    img = ProductImage(product=product, alt_text=product.title, sort_order=0)
                    img.image.save(f"{slugify(product.title)}.jpg", image_file, save=True)

        self.stdout.write(self.style.SUCCESS(f"Seeded demo products. New products created: {created}"))

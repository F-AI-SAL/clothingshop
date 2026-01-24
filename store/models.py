from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.utils import timezone


# =========================
# CATEGORY
# =========================
class Category(models.Model):
    history = HistoricalRecords()
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, blank=True)

    # Admin controlled category card/banner
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    tagline = models.CharField(max_length=120, blank=True)

    # Parent → child (Mega menu support)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children"
    )

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name


# =========================
# PRODUCT
# =========================
class Product(models.Model):
    history = HistoricalRecords()
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products"
    )

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    sku = models.CharField(max_length=60, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)

    # Simple variants (later normalize করা যাবে)
    colors = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma separated. e.g. beige, blue, black"
    )
    sizes = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma separated. e.g. XS, S, M, L, XL"
    )

    is_active = models.BooleanField(default=True)
    is_new = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def color_list(self):
        return [c.strip() for c in self.colors.split(",") if c.strip()]

    def size_list(self):
        return [s.strip() for s in self.sizes.split(",") if s.strip()]

    def __str__(self):
        return self.title


# =========================
# PRODUCT IMAGES
# =========================
class ProductImage(models.Model):
    history = HistoricalRecords()
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=150, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.product.title} image"

# =========================
# PRODUCT Variants
# =========================
class ProductVariant(models.Model):
    history = HistoricalRecords()
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    color = models.CharField(max_length=60, blank=True)
    size = models.CharField(max_length=60, blank=True)

    stock_qty = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("product", "color", "size")
        ordering = ["product_id", "color", "size"]

    def __str__(self):
        return f"{self.product.title} ({self.color or '-'}, {self.size or '-'})"
# =========================
# HOME HERO BANNER
# =========================
class HomeBanner(models.Model):
    history = HistoricalRecords()
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    image = models.ImageField(upload_to="banners/")

    button_text = models.CharField(max_length=50, default="Shop Now")
    button_link = models.CharField(max_length=200, default="/products/")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


# =========================
# FEATURED COLLECTION BANNER (Slider Ready)
# =========================
class FeaturedBanner(models.Model):
    history = HistoricalRecords()
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)

    image = models.ImageField(upload_to="featured/")

    button_text = models.CharField(max_length=50, default="Explore Collection")
    button_link = models.CharField(max_length=200, default="/products/")

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "-created_at"]

    def __str__(self):
        return self.title
class Order(models.Model):
    history = HistoricalRecords()
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("processing", "Processing"),
        ("packaging", "Packaging"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    )

    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)

    address = models.TextField()
    city = models.CharField(max_length=80, blank=True)
    area = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=30, blank=True)

    payment_method = models.CharField(max_length=30, default="cod")  # cod / bkash / nagad / card
    notes = models.TextField(blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} - {self.full_name}"


class OrderItem(models.Model):
    history = HistoricalRecords()
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    qty = models.PositiveIntegerField(default=1)

    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # snapshot (optional)
    color = models.CharField(max_length=60, blank=True)
    size = models.CharField(max_length=60, blank=True)

    def save(self, *args, **kwargs):
        self.line_total = (self.price or 0) * self.qty
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.title} x {self.qty}"

# =========================
# Payments
# =========================
class PaymentTransaction(models.Model):
    history = HistoricalRecords()
    METHOD_CHOICES = (
        ("cod", "Cash on Delivery"),
        ("bkash", "bKash"),
        ("nagad", "Nagad"),
        ("bank", "Bank Transfer"),
    )
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="cod")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reference_id = models.CharField(max_length=120, blank=True)
    proof_image = models.ImageField(upload_to="payments/", blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment #{self.order_id} ({self.get_method_display()})"


# =========================
# Shipping
# =========================
class CourierSettings(models.Model):
    history = HistoricalRecords()
    provider_name = models.CharField(max_length=80, default="Universal Courier")
    merchant_id = models.CharField(max_length=120, blank=True)
    api_key = models.CharField(max_length=200, blank=True)
    api_secret = models.CharField(max_length=200, blank=True)
    base_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.provider_name


class Shipment(models.Model):
    history = HistoricalRecords()
    STATUS_CHOICES = (
        ("created", "Created"),
        ("picked", "Picked"),
        ("in_transit", "In transit"),
        ("delivered", "Delivered"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="shipments")
    courier_name = models.CharField(max_length=80, blank=True)
    merchant_id = models.CharField(max_length=120, blank=True)
    tracking_id = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    label_url = models.URLField(blank=True)
    metadata = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Shipment #{self.order_id} ({self.get_status_display()})"


# =========================
# Manual Notifications
# =========================
class ManualNotificationLog(models.Model):
    history = HistoricalRecords()
    CHANNEL_CHOICES = (
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
    )
    STATUS_CHOICES = (
        ("queued", "Queued"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="notifications")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_channel_display()} for Order #{self.order_id}"

# =========================
# Site Settings + Navbar
# =========================
class SiteSettings(models.Model):
    history = HistoricalRecords()
    brand_name = models.CharField(max_length=120, default="La Rosa")
    brand_tagline = models.CharField(max_length=200, blank=True, default="Formals")
    logo = models.ImageField(upload_to="branding/", blank=True, null=True)

    primary_color = models.CharField(max_length=20, blank=True, help_text="Hex color, e.g. #0f172a")
    accent_color = models.CharField(max_length=20, blank=True, help_text="Hex color, e.g. #f59e0b")

    meta_pixel_id = models.CharField(max_length=80, blank=True)
    meta_pixel_enabled = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Site Settings"


class NavLink(models.Model):
    history = HistoricalRecords()
    LOCATION_CHOICES = (
        ("header", "Header"),
        ("footer", "Footer"),
        ("mobile", "Mobile"),
    )

    label = models.CharField(max_length=120)
    url = models.CharField(max_length=300)
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES, default="header")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    open_new_tab = models.BooleanField(default=False)

    class Meta:
        ordering = ["location", "sort_order", "label"]

    def __str__(self):
        return f"{self.label} ({self.location})"

# =========================
# Consent + GDPR
# =========================
class ConsentRecord(models.Model):
    history = HistoricalRecords()
    CONSENT_CHOICES = (
        ("marketing", "Marketing"),
        ("analytics", "Analytics"),
        ("email", "Email"),
        ("sms", "SMS"),
    )

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    consent_type = models.CharField(max_length=20, choices=CONSENT_CHOICES)
    is_granted = models.BooleanField(default=True)
    source = models.CharField(max_length=120, blank=True, help_text="signup, checkout, popup, etc.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.consent_type} ({'yes' if self.is_granted else 'no'})"


class GdprRequest(models.Model):
    history = HistoricalRecords()
    REQUEST_CHOICES = (
        ("export", "Export"),
        ("delete", "Delete"),
    )
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("rejected", "Rejected"),
    )

    email = models.EmailField()
    request_type = models.CharField(max_length=20, choices=REQUEST_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_request_type_display()} ({self.email})"

# =========================
# Coupon
# =========================
class Coupon(models.Model):
    history = HistoricalRecords()
    TYPE_CHOICES = (("percent", "Percent"), ("fixed", "Fixed"))

    code = models.CharField(max_length=30, unique=True)
    discount_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="percent")
    value = models.DecimalField(max_digits=10, decimal_places=2)

    min_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    start_at = models.DateTimeField(blank=True, null=True)
    end_at = models.DateTimeField(blank=True, null=True)

    max_uses = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    used_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.code


@receiver(pre_save, sender=Order)
def _notify_order_status_change(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        previous = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return

    if previous.status == instance.status:
        return

    from .emails import send_status_update_notification

    send_status_update_notification(instance, previous_status=previous.get_status_display())

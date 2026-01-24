from django.contrib import admin, messages
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from django.utils.html import format_html
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from django.template.response import TemplateResponse
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

from .models import (
    Category,
    Product,
    ProductImage,
    HomeBanner,
    FeaturedBanner,
    Order,
    OrderItem,
    ProductVariant,
    Coupon,
    PaymentTransaction,
    Shipment,
    CourierSettings,
    ManualNotificationLog,
    SiteSettings,
    NavLink,
)


# ============================================================
# OPTIONAL: Admin Dashboard (works only if you wire custom site)
# ============================================================
class StoreAdminSite(admin.AdminSite):
    site_header = "La Rosa Admin"
    site_title = "La Rosa Admin"
    index_title = "Dashboard"

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path("dashboard/", self.admin_view(self.dashboard_view), name="store-dashboard"),
        ]
        return extra + urls

    def dashboard_view(self, request):
        now = timezone.now()
        start = now - timedelta(days=7)

        revenue_7d = Order.objects.filter(created_at__gte=start).aggregate(s=Sum("total"))["s"] or 0
        orders_7d = Order.objects.filter(created_at__gte=start).count()

        by_status = list(
            Order.objects.values("status").annotate(c=Count("id")).order_by("-c")
        )

        top_products = list(
            OrderItem.objects.values("product__title")
            .annotate(q=Sum("qty"))
            .order_by("-q")[:8]
        )

        return TemplateResponse(request, "admin/store/dashboard.html", {
            "revenue_7d": revenue_7d,
            "orders_7d": orders_7d,
            "by_status": by_status,
            "top_products": top_products,
        })


# =========================
# PRODUCT IMAGES INLINE
# =========================
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ("image", "alt_text", "sort_order")
    ordering = ("sort_order",)

# =========================
# ORDER INLINE
# =========================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "qty", "price", "line_total", "color", "size")
    can_delete = False


class PaymentInline(admin.StackedInline):
    model = PaymentTransaction
    extra = 0
    max_num = 1
    can_delete = False
    readonly_fields = ("created_at", "verified_at")


class ShipmentInline(admin.TabularInline):
    model = Shipment
    extra = 0
    readonly_fields = ("created_at",)


class ManualNotificationInline(admin.TabularInline):
    model = ManualNotificationLog
    extra = 0
    readonly_fields = ("created_at", "sent_at", "sent_by")
    can_delete = False


class OrderResource(resources.ModelResource):
    class Meta:
        model = Order
        fields = (
            "id",
            "full_name",
            "phone",
            "email",
            "status",
            "payment_method",
            "subtotal",
            "discount",
            "shipping_cost",
            "total",
            "created_at",
        )


@admin.register(Order)
class OrderAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = OrderResource
    list_display = (
        "id",
        "full_name",
        "phone",
        "status_badge",
        "payment_status",
        "payment_method",
        "items_summary",
        "view_order",
        "quick_actions",
        "total",
        "created_at",
    )
    list_filter = ("status", "payment__status", "payment_method", "created_at")
    search_fields = ("id", "full_name", "phone", "email", "items__product__title")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    inlines = [OrderItemInline, PaymentInline, ShipmentInline, ManualNotificationInline]
    readonly_fields = ("subtotal", "discount", "shipping_cost", "total", "created_at")
    actions = [
        "mark_as_accepted",
        "mark_as_processing",
        "mark_as_packaging",
        "mark_as_shipped",
        "mark_as_delivered",
        "mark_as_cancelled",
        "mark_as_refunded",
        "verify_payment",
        "refund_payment",
        "create_shipment",
        "send_sms_notification",
        "send_whatsapp_notification",
        "anonymize_orders",
    ]

    def _mark_status(self, request, queryset, status_key, label):
        updated = 0
        for order in queryset:
            if order.status == status_key:
                continue
            order.status = status_key
            order.save(update_fields=["status"])
            updated += 1
        self.message_user(request, f"{updated} order(s) marked as {label}.")

    def mark_as_accepted(self, request, queryset):
        self._mark_status(request, queryset, "accepted", "Accepted")
    mark_as_accepted.short_description = "Mark selected orders as Accepted"

    def mark_as_processing(self, request, queryset):
        self._mark_status(request, queryset, "processing", "Processing")
    mark_as_processing.short_description = "Mark selected orders as Processing"

    def mark_as_packaging(self, request, queryset):
        self._mark_status(request, queryset, "packaging", "Packaging")
    mark_as_packaging.short_description = "Mark selected orders as Packaging"

    def mark_as_shipped(self, request, queryset):
        self._mark_status(request, queryset, "shipped", "Shipped")
    mark_as_shipped.short_description = "Mark selected orders as Shipped"

    def mark_as_delivered(self, request, queryset):
        self._mark_status(request, queryset, "delivered", "Delivered")
    mark_as_delivered.short_description = "Mark selected orders as Delivered"

    def mark_as_cancelled(self, request, queryset):
        self._mark_status(request, queryset, "cancelled", "Cancelled")
    mark_as_cancelled.short_description = "Mark selected orders as Cancelled"

    def mark_as_refunded(self, request, queryset):
        self._mark_status(request, queryset, "refunded", "Refunded")
    mark_as_refunded.short_description = "Mark selected orders as Refunded"

    def payment_status(self, obj):
        if hasattr(obj, "payment"):
            return obj.payment.get_status_display()
        return "N/A"
    payment_status.short_description = "Payment"

    def status_badge(self, obj):
        color_map = {
            "pending": "#f59e0b",
            "accepted": "#2563eb",
            "processing": "#0ea5e9",
            "packaging": "#7c3aed",
            "shipped": "#10b981",
            "delivered": "#16a34a",
            "cancelled": "#ef4444",
            "refunded": "#6b7280",
        }
        color = color_map.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:999px;font-size:11px;">{}</span>',
            color,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def items_summary(self, obj):
        items = obj.items.all()
        if not items:
            return "No items"
        parts = []
        for item in items:
            variant = []
            if item.color:
                variant.append(item.color)
            if item.size:
                variant.append(item.size)
            variant_text = f" ({', '.join(variant)})" if variant else ""
            parts.append(f"{item.product.title}{variant_text} x{item.qty}")
        return ", ".join(parts)
    items_summary.short_description = "Items"

    def anonymize_orders(self, request, queryset):
        updated = 0
        for order in queryset:
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
        self.message_user(request, f"{updated} order(s) anonymized.")
    anonymize_orders.short_description = "GDPR: anonymize selected orders"

    def quick_actions(self, obj):
        actions = [
            ("accepted", "Accept", "#2563eb"),
            ("processing", "Process", "#0ea5e9"),
            ("packaging", "Pack", "#7c3aed"),
            ("shipped", "Ship", "#10b981"),
            ("cancelled", "Cancel", "#ef4444"),
            ("refunded", "Refund", "#6b7280"),
        ]
        links = []
        for status, label, color in actions:
            url = reverse("admin:store_order_quick_status", args=[obj.id, status])
            links.append(
                format_html(
                    '<a href="{}" style="background:{};color:#fff;padding:2px 6px;border-radius:6px;font-size:11px;margin-right:4px;">{}</a>',
                    url,
                    color,
                    label,
                )
            )
        return mark_safe("".join(links))
    quick_actions.short_description = "Quick Actions"

    def view_order(self, obj):
        url = reverse("admin:store_order_change", args=[obj.id])
        return format_html(
            '<a href="{}" style="padding:2px 6px;border-radius:6px;border:1px solid #e5e7eb;font-size:11px;">View</a>',
            url,
        )
    view_order.short_description = "Details"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("payment").prefetch_related("items__product")

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:order_id>/status/<str:status>/",
                self.admin_site.admin_view(self.quick_status_view),
                name="store_order_quick_status",
            ),
        ]
        return custom + urls

    def quick_status_view(self, request, order_id, status):
        valid = {key for key, _ in Order.STATUS_CHOICES}
        if status not in valid:
            self.message_user(request, "Invalid status.", level=messages.ERROR)
            return redirect(request.META.get("HTTP_REFERER", ""))
        order = get_object_or_404(Order, id=order_id)
        if order.status != status:
            order.status = status
            order.save(update_fields=["status"])
        return redirect(request.META.get("HTTP_REFERER", ""))

    def _ensure_payment(self, order):
        if hasattr(order, "payment"):
            return order.payment
        return PaymentTransaction.objects.create(
            order=order,
            method=order.payment_method,
            amount=order.total,
        )

    def verify_payment(self, request, queryset):
        updated = 0
        for order in queryset:
            payment = self._ensure_payment(order)
            if payment.status == "verified":
                continue
            payment.status = "verified"
            payment.verified_at = timezone.now()
            payment.save(update_fields=["status", "verified_at"])
            updated += 1
        self.message_user(request, f"{updated} payment(s) marked as Verified.")
    verify_payment.short_description = "Verify payment for selected orders"

    def refund_payment(self, request, queryset):
        updated = 0
        for order in queryset:
            payment = self._ensure_payment(order)
            if payment.status == "refunded":
                continue
            payment.status = "refunded"
            payment.save(update_fields=["status"])
            if order.status != "refunded":
                order.status = "refunded"
                order.save(update_fields=["status"])
            updated += 1
        self.message_user(request, f"{updated} payment(s) marked as Refunded.")
    refund_payment.short_description = "Refund payment for selected orders"

    def create_shipment(self, request, queryset):
        settings_obj = CourierSettings.objects.filter(is_active=True).first()
        updated = 0
        for order in queryset:
            Shipment.objects.create(
                order=order,
                courier_name=settings_obj.provider_name if settings_obj else "",
                merchant_id=settings_obj.merchant_id if settings_obj else "",
                status="created",
            )
            if order.status == "pending":
                order.status = "processing"
                order.save(update_fields=["status"])
            updated += 1
        self.message_user(request, f"{updated} shipment(s) created.")
    create_shipment.short_description = "Create shipment (universal courier)"

    def _log_manual_notification(self, request, queryset, channel):
        updated = 0
        for order in queryset:
            message = f"Order #{order.id} status: {order.get_status_display()}, total PKR {order.total}."
            ManualNotificationLog.objects.create(
                order=order,
                channel=channel,
                message=message,
                status="sent",
                sent_by=request.user,
                sent_at=timezone.now(),
            )
            updated += 1
        label = channel.upper()
        self.message_user(request, f"{updated} {label} notification(s) logged as sent.")

    def send_sms_notification(self, request, queryset):
        self._log_manual_notification(request, queryset, "sms")
    send_sms_notification.short_description = "Log manual SMS notification as sent"

    def send_whatsapp_notification(self, request, queryset):
        self._log_manual_notification(request, queryset, "whatsapp")
    send_whatsapp_notification.short_description = "Log manual WhatsApp notification as sent"


@admin.register(CourierSettings)
class CourierSettingsAdmin(admin.ModelAdmin):
    list_display = ("provider_name", "merchant_id", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("provider_name", "merchant_id")
    ordering = ("-updated_at",)


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("order", "courier_name", "status", "tracking_id", "created_at")
    list_filter = ("status", "courier_name")
    search_fields = ("order__id", "tracking_id")
    ordering = ("-created_at",)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("order", "method", "status", "amount", "reference_id", "created_at")
    list_filter = ("status", "method")
    search_fields = ("order__id", "reference_id")
    ordering = ("-created_at",)


@admin.register(ManualNotificationLog)
class ManualNotificationLogAdmin(admin.ModelAdmin):
    list_display = ("order", "channel", "status", "sent_by", "sent_at")
    list_filter = ("channel", "status")
    search_fields = ("order__id", "message")
    ordering = ("-created_at",)


# =========================
# HOME HERO BANNER
# =========================
@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "created_at")
    list_editable = ("is_active",)
    search_fields = ("title",)
    ordering = ("-created_at",)


# =========================
# FEATURED COLLECTION BANNER
# =========================
@admin.register(FeaturedBanner)
class FeaturedBannerAdmin(admin.ModelAdmin):
    list_display = ("preview", "title", "is_active", "sort_order", "created_at")
    list_editable = ("is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("title", "subtitle")
    ordering = ("sort_order", "-created_at")

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:42px;width:72px;object-fit:cover;'
                'border-radius:8px;border:1px solid #e5e7eb;" />',
                obj.image.url
            )
        return "—"
    preview.short_description = "Preview"


# =========================
# CATEGORY
# =========================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "sort_order")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")
    ordering = ("parent__name", "sort_order", "name")
    prepopulated_fields = {"slug": ("name",)}

    fieldsets = (
        (None, {"fields": ("name", "slug", "parent", "is_active", "sort_order")}),
        ("Category Card / Banner", {"fields": ("image", "tagline"), "classes": ("collapse",)}),
    )

# =========================
# PRODUCT VARIANTS INLINE (Inventory per size/color)
# =========================
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ("color", "size", "stock_qty", "sku", "is_active")
    ordering = ("color", "size")

# =========================
# PRODUCT
# =========================
class ProductResource(resources.ModelResource):
    class Meta:
        model = Product
        fields = ("id", "title", "sku", "price", "colors", "sizes", "is_active", "is_new", "created_at")


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = ProductResource
    list_display = ("title", "category", "price", "stock_summary", "is_active", "is_new", "created_at")
    list_filter = ("is_active", "is_new", "category")
    search_fields = ("title", "sku")
    ordering = ("-created_at",)
    prepopulated_fields = {"slug": ("title",)}

    # ✅ correct place for inlines
    inlines = [ProductImageInline, ProductVariantInline]

    fieldsets = (
        (None, {"fields": ("title", "slug", "category", "sku")}),
        ("Pricing & Description", {"fields": ("price", "description")}),
        ("Variants (simple list)", {"fields": ("colors", "sizes"), "classes": ("collapse",)}),
        ("Status", {"fields": ("is_active", "is_new")}),
    )

    class Media:
        js = ("store/admin/sortable.js",)

    def stock_summary(self, obj):
        variants = obj.variants.all()
        if variants.exists():
            total = sum(v.stock_qty for v in variants)
            return f"{total} in stock"
        return "No variants"
    stock_summary.short_description = "Stock"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("variants")


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("brand_name", "brand_tagline", "updated_at")
    readonly_fields = ("updated_at",)
    fieldsets = (
        ("Branding", {"fields": ("brand_name", "brand_tagline", "logo")}),
        ("Colors", {"fields": ("primary_color", "accent_color"), "classes": ("collapse",)}),
        ("Marketing", {"fields": ("meta_pixel_enabled", "meta_pixel_id"), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()


@admin.register(NavLink)
class NavLinkAdmin(admin.ModelAdmin):
    list_display = ("label", "location", "url", "is_active", "sort_order")
    list_filter = ("location", "is_active")
    search_fields = ("label", "url")
    ordering = ("location", "sort_order")

# =========================
# Coupon
# ========================= 
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "value", "is_active", "min_subtotal", "used_count", "max_uses")
    list_filter = ("is_active", "discount_type")
    search_fields = ("code",)
    ordering = ("-id",)      


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    date_hierarchy = "action_time"
    list_display = ("action_time", "user", "content_type", "object_repr", "action_flag")
    list_filter = ("action_flag", "content_type", "user")
    search_fields = ("object_repr", "change_message", "user__username")
    readonly_fields = ("action_time", "user", "content_type", "object_id", "object_repr", "action_flag", "change_message")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

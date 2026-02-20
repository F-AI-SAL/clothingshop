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
    ConsentRecord,
    GdprRequest,
    PaymentProviderConfig,
    CourierProviderConfig,
    MessagingConfig,
    PaymentWebhookEvent,
    PaymentReconciliationReport,
    MessageTemplate,
)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "qty", "price", "color", "size", "line_total")
    readonly_fields = ("line_total",)


class PaymentInline(admin.StackedInline):
    model = PaymentTransaction
    extra = 0
    max_num = 1


class ShipmentInline(admin.StackedInline):
    model = Shipment
    extra = 0


class ManualNotificationInline(admin.TabularInline):
    model = ManualNotificationLog
    extra = 0
    readonly_fields = ("sent_by", "sent_at", "created_at")


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "alt_text", "sort_order")
    sortable_field_name = "sort_order"


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
        "resend_email",
        "anonymize_orders",
    ]

    def _mark_status(self, request, queryset, status_key, label):
        updated = 0
        skipped = 0
        for order in queryset:
            if order.status == status_key:
                continue
            if not order.is_valid_transition(status_key):
                skipped += 1
                continue
            order.status = status_key
            order.save(update_fields=["status"])
            updated += 1
        if skipped:
            self.message_user(request, f"{skipped} order(s) skipped due to invalid transition.", level=messages.WARNING)
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

    def view_order(self, obj):
        url = reverse("admin:store_order_detail", args=[obj.id])
        return format_html(
            '<a href="{}" style="padding:2px 6px;border-radius:6px;border:1px solid #e5e7eb;font-size:11px;">Details</a>',
            url,
        )
    view_order.short_description = "Details"

    def order_detail_view(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        return TemplateResponse(request, "admin/store/order_detail.html", {"order": order})

    def view_order(self, obj):
        url = reverse("admin:store_order_change", args=[obj.id])
        return format_html(
            '<a href="{}" style="padding:2px 6px;border-radius:6px;border:1px solid #e5e7eb;font-size:11px;">View</a>',
            url,
        )
    view_order.short_description = "Details"

    def quick_actions(self, obj):
        url = reverse("admin:store_order_quick_status", args=[obj.id])
        csrf_token = self._get_csrf_token()
        next_url = getattr(self, "_changelist_path", reverse("admin:store_order_changelist"))
        return format_html(
            '<form action="{}" method="post" style="display:flex;gap:4px;flex-wrap:wrap;">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
            '<input type="hidden" name="next" value="{}" />'
            '<button name="status" value="accepted" style="background:#2563eb;color:#fff;padding:2px 6px;border-radius:6px;font-size:11px;border:none;">Accept</button>'
            '<button name="status" value="processing" style="background:#0ea5e9;color:#fff;padding:2px 6px;border-radius:6px;font-size:11px;border:none;">Process</button>'
            '<button name="status" value="packaging" style="background:#7c3aed;color:#fff;padding:2px 6px;border-radius:6px;font-size:11px;border:none;">Pack</button>'
            '<button name="status" value="shipped" style="background:#10b981;color:#fff;padding:2px 6px;border-radius:6px;font-size:11px;border:none;">Ship</button>'
            '<button name="status" value="cancelled" style="background:#ef4444;color:#fff;padding:2px 6px;border-radius:6px;font-size:11px;border:none;">Cancel</button>'
            '<button name="status" value="refunded" style="background:#6b7280;color:#fff;padding:2px 6px;border-radius:6px;font-size:11px;border:none;">Refund</button>'
            '</form>',
            url,
            csrf_token,
            next_url,
        )
    quick_actions.short_description = "Quick Actions"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("payment").prefetch_related("items__product")

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:order_id>/status/",
                self.admin_site.admin_view(self.quick_status_view),
                name="store_order_quick_status",
            ),
        ]
        return custom + urls

    def quick_status_view(self, request, order_id):
        if request.method != "POST":
            return redirect(reverse("admin:store_order_changelist"))
        valid = {key for key, _ in Order.STATUS_CHOICES}
        status = request.POST.get("status")
        if status not in valid:
            self.message_user(request, "Invalid status.", level=messages.ERROR)
            return redirect(request.POST.get("next") or reverse("admin:store_order_changelist"))
        order = get_object_or_404(Order, id=order_id)
        if order.status != status:
            if not order.is_valid_transition(status):
                self.message_user(request, "Invalid status transition.", level=messages.ERROR)
                return redirect(request.POST.get("next") or reverse("admin:store_order_changelist"))
            order.status = status
            order.save(update_fields=["status"])
        return redirect(request.POST.get("next") or reverse("admin:store_order_changelist"))

    def _get_csrf_token(self):
        from django.middleware.csrf import get_token
        request = getattr(self, "_request_for_csrf", None)
        if not request:
            return ""
        return get_token(request)

    def changelist_view(self, request, extra_context=None):
        self._request_for_csrf = request
        self._changelist_path = request.get_full_path()
        return super().changelist_view(request, extra_context=extra_context)

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
            message = f"Order #{order.id} status: {order.get_status_display()}, total BDT {order.total}."
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

    def resend_email(self, request, queryset):
        updated = 0
        for order in queryset:
            if not order.email:
                continue
            from .emails import send_order_created_notifications
            send_order_created_notifications(order)
            updated += 1
        self.message_user(request, f"{updated} email(s) sent.")
    resend_email.short_description = "Resend order confirmation email"


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
        js = ("store/admin/sortable.min.js", "store/admin/sortable.js")

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


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ("consent_type", "email", "phone", "is_granted", "source", "created_at")
    list_filter = ("consent_type", "is_granted")
    search_fields = ("email", "phone", "source")
    ordering = ("-created_at",)


@admin.register(GdprRequest)
class GdprRequestAdmin(admin.ModelAdmin):
    list_display = ("email", "request_type", "status", "created_at", "completed_at")
    list_filter = ("request_type", "status")
    search_fields = ("email", "notes")
    ordering = ("-created_at",)
    actions = ["mark_processing", "mark_completed", "anonymize_orders_by_email"]

    def mark_processing(self, request, queryset):
        queryset.update(status="processing")
        self.message_user(request, "Selected requests set to processing.")
    mark_processing.short_description = "Mark selected as Processing"

    def mark_completed(self, request, queryset):
        queryset.update(status="completed", completed_at=timezone.now())
        self.message_user(request, "Selected requests set to completed.")
    mark_completed.short_description = "Mark selected as Completed"

    def anonymize_orders_by_email(self, request, queryset):
        emails = set(queryset.values_list("email", flat=True))
        updated = 0
        for order in Order.objects.filter(email__in=emails):
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
        self.message_user(request, f"Anonymized {updated} order(s) for selected GDPR emails.")
    anonymize_orders_by_email.short_description = "GDPR: anonymize orders for selected emails"

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


@admin.register(PaymentProviderConfig)
class PaymentProviderConfigAdmin(SimpleHistoryAdmin):
    list_display = ("provider", "is_live", "updated_at")
    list_filter = ("provider", "is_live")


@admin.register(CourierProviderConfig)
class CourierProviderConfigAdmin(SimpleHistoryAdmin):
    list_display = ("provider", "is_active", "updated_at")
    list_filter = ("provider", "is_active")


@admin.register(MessagingConfig)
class MessagingConfigAdmin(SimpleHistoryAdmin):
    list_display = ("sms_provider", "whatsapp_provider", "updated_at")


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(SimpleHistoryAdmin):
    list_display = ("provider", "event_id", "received_at")
    search_fields = ("provider", "event_id")



@admin.register(PaymentReconciliationReport)
class PaymentReconciliationReportAdmin(SimpleHistoryAdmin):
    list_display = ("run_at", "total_pending", "reconciled", "failed")
    ordering = ("-run_at",)



@admin.register(MessageTemplate)
class MessageTemplateAdmin(SimpleHistoryAdmin):
    list_display = ("channel", "event", "is_active", "preview_email")
    list_filter = ("channel", "event", "is_active")
    search_fields = ("subject", "body")

    def preview_email(self, obj):
        if obj.channel != "email":
            return "-"
        url = reverse("admin:store_message_template_preview", args=[obj.id])
        return format_html("<a href=\"{}\">Preview</a>", url)
    preview_email.short_description = "Preview"

